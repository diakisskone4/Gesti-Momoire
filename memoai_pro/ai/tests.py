import json
from types import SimpleNamespace
from unittest import mock

import anthropic
import httpx
import httpx2
import openai
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from users.models import User
from . import services


def fake_response(text, stop_reason='end_turn'):
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type='text', text=text)])


def api_error(cls, status):
    response = httpx2.Response(status, request=httpx2.Request('POST', 'https://api.anthropic.com/v1/messages'))
    return cls('erreur', response=response, body=None)


@override_settings(AI_PROVIDER='anthropic', ANTHROPIC_API_KEY='test-key', AI_MODEL='claude-opus-5-5')
class AIViewsTests(APITestCase):
    def setUp(self):
        services._client.cache_clear()
        self.user = User.objects.create_user('etu@test.com', 'Motdepasse-Solide-2026', first_name='A', last_name='B')
        self.client.force_authenticate(self.user)
        patcher = mock.patch.object(services, '_client')
        self.create = patcher.start().return_value.beta.messages.create
        self.addCleanup(patcher.stop)

    def test_chat_sends_fallback_and_returns_text(self):
        self.create.return_value = fake_response('Bonjour')
        res = self.client.post('/ai/chat/', {'message': 'Salut'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['response'], 'Bonjour')
        kwargs = self.create.call_args.kwargs
        self.assertEqual(kwargs['model'], 'claude-opus-5-5')
        self.assertEqual(kwargs['fallbacks'], 'default')

    def test_verify_returns_structured_json(self):
        payload = {'score': 70, 'summary': 'ok', 'issues': []}
        self.create.return_value = fake_response(json.dumps(payload))
        res = self.client.post('/ai/verify/', {'content': 'Texte'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, payload)
        self.assertEqual(self.create.call_args.kwargs['output_config']['format']['type'], 'json_schema')

    def test_refusal_is_reported(self):
        self.create.return_value = fake_response('', stop_reason='refusal')
        res = self.client.post('/ai/summarize/', {'text': 'Texte'})
        self.assertEqual(res.status_code, 422)

    def test_billing_error_is_hidden_behind_friendly_message(self):
        self.create.side_effect = api_error(anthropic.APIStatusError, 402)
        res = self.client.post('/ai/translate/', {'text': 'Texte'})
        self.assertEqual(res.status_code, 503)
        self.assertIn('crédit', res.data['error'])

    def test_invalid_key(self):
        self.create.side_effect = api_error(anthropic.AuthenticationError, 401)
        res = self.client.post('/ai/reformulate/', {'text': 'Texte'})
        self.assertEqual(res.status_code, 503)


@override_settings(AI_PROVIDER='anthropic', ANTHROPIC_API_KEY='')
class AIMissingKeyTests(APITestCase):
    def test_missing_key(self):
        services._client.cache_clear()
        user = User.objects.create_user('etu@test.com', 'Motdepasse-Solide-2026', first_name='A', last_name='B')
        self.client.force_authenticate(user)
        res = self.client.post('/ai/chat/', {'message': 'Salut'})
        self.assertEqual(res.status_code, 503)
        self.assertIn('ANTHROPIC_API_KEY', res.data['error'])


PLAN = {
    'chapters': [{'title': 'Cadre théorique', 'order': 1, 'sections': [{'title': 'Définitions', 'subsections': []}]}],
    'figures': [], 'tables': [], 'references': [], 'appendices': [], 'glossary': [],
}


@override_settings(AI_PROVIDER='anthropic', ANTHROPIC_API_KEY='test-key', AI_MODEL='claude-opus-5-5', CELERY_TASK_ALWAYS_EAGER=True)
class PlanGenerationTests(APITestCase):
    def setUp(self):
        from celery import current_app
        current_app.conf.task_always_eager = True
        self.addCleanup(setattr, current_app.conf, 'task_always_eager', False)
        services._client.cache_clear()
        from projects.models import Project
        self.user = User.objects.create_user('etu@test.com', 'Motdepasse-Solide-2026', first_name='A', last_name='B')
        from modeles.models import MemoirTemplate, TemplatePurchase
        template = MemoirTemplate.objects.get(slug='licence-classique')
        TemplatePurchase.objects.create(user=self.user, template=template, amount=5000, status='PAID')
        self.project = Project.objects.create(user=self.user, title='Mobile money', theme='Mobile money au Mali',
                                              template=template)
        self.client.force_authenticate(self.user)
        patcher = mock.patch.object(services, '_client')
        self.create = patcher.start().return_value.beta.messages.create
        self.addCleanup(patcher.stop)

    def test_plan_creates_chapters_and_sections_without_redis(self):
        self.create.return_value = fake_response(json.dumps(PLAN))
        res = self.client.post('/ai/generate-plan/', {'project_id': self.project.id})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['status'], 'COMPLETED')
        # Pages liminaires et fin (bibliographie, annexes) du modèle + chapitre IA et sa section.
        titles = list(self.project.chapters.filter(parent=None).order_by('order').values_list('title', flat=True))
        self.assertEqual(titles[0], 'Dédicace')
        self.assertIn('Cadre théorique', titles)
        self.assertEqual(titles[-2:], ['Bibliographie', 'Annexes'])
        self.assertTrue(self.project.chapters.filter(title='Définitions', parent__title='Cadre théorique').exists())
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, 'IN_PROGRESS')

        status = self.client.get(f"/ai/task/{res.data['ai_task_id']}/")
        self.assertEqual(status.data['status'], 'COMPLETED')

    def test_ai_failure_is_recorded(self):
        self.create.side_effect = services.AIError('Clé manquante', 503)
        res = self.client.post('/ai/generate-plan/', {'project_id': self.project.id})
        self.assertEqual(res.data['status'], 'FAILED')
        self.assertEqual(res.data['error'], 'Clé manquante')

    def test_broker_down_returns_503(self):
        from kombu.exceptions import OperationalError
        with mock.patch('ai.tasks.generate_plan_task.delay', side_effect=OperationalError('down')):
            res = self.client.post('/ai/generate-plan/', {'project_id': self.project.id})
        self.assertEqual(res.status_code, 503)


@override_settings(AI_PROVIDER='anthropic', ANTHROPIC_API_KEY='test-key', AI_MODEL='claude-opus-5-5')
class CreditErrorTests(APITestCase):
    def test_low_credit_400_is_reported_as_credit_problem(self):
        services._client.cache_clear()
        user = User.objects.create_user('etu@test.com', 'Motdepasse-Solide-2026', first_name='A', last_name='B')
        self.client.force_authenticate(user)
        response = httpx2.Response(400, request=httpx2.Request('POST', 'https://api.anthropic.com/v1/messages'))
        err = anthropic.BadRequestError(
            'Your credit balance is too low to access the Anthropic API.', response=response,
            body={'type': 'error', 'error': {'type': 'invalid_request_error'}})
        with mock.patch.object(services, '_client') as client:
            client.return_value.beta.messages.create.side_effect = err
            res = self.client.post('/ai/chat/', {'message': 'Salut'})
        self.assertEqual(res.status_code, 503)
        self.assertIn('crédit', res.data['error'])


def fake_chat_completion(text, finish_reason='stop'):
    message = SimpleNamespace(content=text)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish_reason)])


@override_settings(AI_PROVIDER='openrouter', OPENAI_API_KEY='test-key', AI_MODEL='openai/gpt-4')
class OpenRouterTests(APITestCase):
    def setUp(self):
        services._openrouter_client.cache_clear()
        self.user = User.objects.create_user('etu@test.com', 'Motdepasse-Solide-2026', first_name='A', last_name='B')
        self.client.force_authenticate(self.user)
        patcher = mock.patch.object(services, '_openrouter_client')
        self.create = patcher.start().return_value.chat.completions.create
        self.addCleanup(patcher.stop)

    def test_chat(self):
        self.create.return_value = fake_chat_completion('Bonjour')
        res = self.client.post('/ai/chat/', {'message': 'Salut'})
        self.assertEqual(res.data['response'], 'Bonjour')
        self.assertEqual(self.create.call_args.kwargs['model'], 'openai/gpt-4')

    def test_json_wrapped_in_text_is_extracted(self):
        payload = {'score': 80, 'summary': 'ok', 'issues': []}
        self.create.return_value = fake_chat_completion('Voici :\n```json\n' + json.dumps(payload) + '\n```')
        res = self.client.post('/ai/verify/', {'content': 'Texte'})
        self.assertEqual(res.data, payload)

    def test_invalid_json_gives_clear_error(self):
        self.create.return_value = fake_chat_completion('pas du json')
        res = self.client.post('/ai/verify/', {'content': 'Texte'})
        self.assertEqual(res.status_code, 502)

    def test_no_credit(self):
        response = httpx.Response(402, request=httpx.Request('POST', 'https://openrouter.ai/api/v1/chat/completions'))
        self.create.side_effect = openai.APIStatusError('no credits', response=response, body=None)
        res = self.client.post('/ai/chat/', {'message': 'Salut'})
        self.assertEqual(res.status_code, 503)
        self.assertIn('OpenRouter', res.data['error'])


def status_error(status):
    response = httpx.Response(status, request=httpx.Request('POST', 'https://openrouter.ai/api/v1/chat/completions'))
    return openai.APIStatusError('erreur', response=response, body=None)


@override_settings(AI_PROVIDER='openrouter', OPENAI_API_KEY='test-key', AI_MODEL='a/principal:free',
                   AI_FALLBACK_MODELS=['b/secours:free', 'c/dernier:free'], AI_SATURATION_RETRY_DELAY=0)
class OpenRouterFallbackTests(APITestCase):
    def setUp(self):
        services._openrouter_client.cache_clear()
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = User.objects.create_user('etu@test.com', 'Motdepasse-Solide-2026', first_name='A', last_name='B')
        self.client.force_authenticate(self.user)
        patcher = mock.patch.object(services, '_openrouter_client')
        self.create = patcher.start().return_value.chat.completions.create
        self.addCleanup(patcher.stop)

    def test_saturated_model_falls_back_to_next(self):
        self.create.side_effect = [status_error(429), status_error(404), fake_chat_completion('Réponse')]
        res = self.client.post('/ai/chat/', {'message': 'Salut'})
        self.assertEqual(res.data['response'], 'Réponse')
        self.assertEqual([c.kwargs['model'] for c in self.create.call_args_list],
                         ['a/principal:free', 'b/secours:free', 'c/dernier:free'])

    def test_empty_answer_falls_back(self):
        self.create.side_effect = [fake_chat_completion(''), fake_chat_completion('Ok')]
        self.assertEqual(self.client.post('/ai/chat/', {'message': 'Salut'}).data['response'], 'Ok')

    def test_all_saturated_gives_clear_429(self):
        # 3 modèles saturés, puis la seconde chance sur le premier échoue aussi.
        self.create.side_effect = [status_error(429)] * 4
        res = self.client.post('/ai/chat/', {'message': 'Salut'})
        self.assertEqual(res.status_code, 429)
        self.assertIn('saturés', res.data['error'])
        self.assertEqual(res['Retry-After'], '60')
        self.assertEqual(self.create.call_count, 4)

    def test_second_chance_after_saturation(self):
        self.create.side_effect = [status_error(429)] * 3 + [fake_chat_completion('Enfin')]
        res = self.client.post('/ai/translate/', {'text': 'Bonjour', 'target_lang': 'en'})
        self.assertEqual(res.data['translation'], 'Enfin')

    def test_saturated_models_are_tried_last_afterwards(self):
        self.create.side_effect = [status_error(429), fake_chat_completion('Ok')]
        self.client.post('/ai/chat/', {'message': 'Salut'})
        self.create.reset_mock(side_effect=True)
        self.create.return_value = fake_chat_completion('Ok')
        self.client.post('/ai/reformulate/', {'text': 'Texte'})
        # Le modèle principal, saturé juste avant, n'est pas réinterrogé en premier.
        self.assertEqual(self.create.call_args_list[0].kwargs['model'], 'b/secours:free')

    def test_daily_quota_stops_immediately_and_is_remembered(self):
        response = httpx.Response(429, request=httpx.Request('POST', 'https://openrouter.ai/api/v1/chat/completions'))
        self.create.side_effect = openai.APIStatusError(
            'Rate limit exceeded: free-models-per-day', response=response, body=None)
        res = self.client.post('/ai/chat/', {'message': 'Salut'})
        self.assertEqual(res.status_code, 429)
        self.assertIn('quota quotidien', res.data['error'])
        self.assertIn('Retry-After', res)
        self.assertEqual(self.create.call_count, 1)
        # Requête suivante : refusée sans consommer de quota.
        res = self.client.post('/ai/translate/', {'text': 'Bonjour'})
        self.assertEqual(res.status_code, 429)
        self.assertEqual(self.create.call_count, 1)

    def test_invalid_key_is_not_retried(self):
        self.create.side_effect = [status_error(401)]
        self.assertEqual(self.client.post('/ai/chat/', {'message': 'Salut'}).status_code, 503)
        self.assertEqual(self.create.call_count, 1)


@override_settings(AI_PROVIDER='openrouter', OPENAI_API_KEY='test-key', AI_MODEL='a/m', AI_FALLBACK_MODELS=[])
class GenerationAccessTests(APITestCase):
    def setUp(self):
        from modeles.models import MemoirTemplate
        from projects.models import Project
        services._openrouter_client.cache_clear()
        self.user = User.objects.create_user('etu@test.com', 'Motdepasse-Solide-2026', first_name='A', last_name='B')
        self.template = MemoirTemplate.objects.get(slug='master-gestion-economie')
        self.project = Project.objects.create(user=self.user, title='Mobile money', theme='Mobile money', desired_pages=40)
        self.client.force_authenticate(self.user)
        patcher = mock.patch.object(services, '_openrouter_client')
        self.create = patcher.start().return_value.chat.completions.create
        self.addCleanup(patcher.stop)

    def buy_and_apply(self):
        from modeles.models import TemplatePurchase
        TemplatePurchase.objects.create(user=self.user, template=self.template, amount=5000, status='PAID')
        self.client.post(f'/modeles/{self.template.slug}/apply/', {'project_id': self.project.id})

    def test_plan_requires_paid_template(self):
        res = self.client.post('/ai/generate-plan/', {'project_id': self.project.id})
        self.assertEqual(res.status_code, 402)
        res = self.client.post(f'/projects/projects/{self.project.id}/generate_plan/')
        self.assertEqual(res.status_code, 402)
        self.create.assert_not_called()

    def test_content_requires_paid_template(self):
        from projects.models import Chapter
        chapter = Chapter.objects.create(project=self.project, title='Chapitre 1')
        res = self.client.post(f'/projects/chapters/{chapter.id}/generate_content/')
        self.assertEqual(res.status_code, 402)
        self.create.assert_not_called()

    def test_plan_refused_when_student_already_wrote_text(self):
        from projects.models import Chapter
        self.buy_and_apply()
        Chapter.objects.filter(project=self.project, title='Remerciements').update(content='Merci à mes parents.')
        res = self.client.post('/ai/generate-plan/', {'project_id': self.project.id})
        self.assertEqual(res.status_code, 400)
        self.assertIn('déjà du texte', res.data['error'])

    def test_content_fills_only_empty_parts(self):
        from projects.models import Chapter
        self.buy_and_apply()
        chapter = Chapter.objects.get(project=self.project, title__startswith='Chapitre 1', parent=None)
        sections = list(chapter.children.order_by('order'))
        sections[0].content = 'Mon propre texte.'
        sections[0].save()
        self.create.return_value = fake_chat_completion(
            '### INTRODUCTION DU CHAPITRE\nCe chapitre présente...\n'
            '### SECTION 1 — x\nNe doit pas écraser.\n### SECTION 2 — y\nRevue empirique rédigée.'
        )
        res = self.client.post(f'/projects/chapters/{chapter.id}/generate_content/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['written'], 2)
        for obj in (sections[0], sections[1], chapter):
            obj.refresh_from_db()
        self.assertEqual(sections[0].content, 'Mon propre texte.')
        self.assertEqual(sections[1].content, 'Revue empirique rédigée.')
        self.assertTrue(chapter.content.startswith('Ce chapitre'))
        prompt = self.create.call_args.kwargs['messages'][1]['content']
        self.assertIn('Revue empirique', prompt)  # titre de section du modèle transmis à l'IA

    def test_dedication_and_acknowledgements_are_never_written(self):
        from projects.models import Chapter
        self.buy_and_apply()
        for title in ('Dédicace', 'Remerciements'):
            page = Chapter.objects.get(project=self.project, title=title)
            res = self.client.post(f'/projects/chapters/{page.id}/generate_content/')
            self.assertEqual(res.status_code, 400)
            self.assertIn('personnels', res.data['error'])
        self.create.assert_not_called()

    def test_abstract_and_acronyms_written_from_existing_text(self):
        from projects.models import Chapter
        self.buy_and_apply()
        Chapter.objects.filter(project=self.project, title__startswith='Chapitre 1', parent=None).update(
            content="Le mobile money, proposé par l'ARTP et la BCEAO, transforme l'inclusion financière. " * 10)
        resume = Chapter.objects.get(project=self.project, title='Résumé')
        sigles = Chapter.objects.get(project=self.project, title='Sigles et abréviations')

        self.create.return_value = fake_chat_completion(
            '**Résumé** : cette étude analyse le mobile money.\n\nMots-clés : mobile money, inclusion\n\n'
            'Abstract\nThis study analyses mobile money.\n\nKeywords: mobile money')
        res = self.client.post(f'/projects/chapters/{resume.id}/generate_content/')
        self.assertEqual(res.status_code, 200, res.data)
        resume.refresh_from_db()
        self.assertTrue(resume.content.startswith('Résumé : cette étude'))  # sans astérisques
        self.assertIn('Abstract', resume.content)
        self.assertIn('mobile money', self.create.call_args.kwargs['messages'][1]['content'])  # texte réel transmis

        self.create.return_value = fake_chat_completion('ARTP : Autorité de régulation\nBCEAO : Banque centrale')
        res = self.client.post(f'/projects/chapters/{sigles.id}/generate_content/')
        self.assertEqual(res.status_code, 200, res.data)
        sigles.refresh_from_db()
        self.assertIn('BCEAO : Banque centrale', sigles.content)

    def test_abstract_needs_written_chapters_first(self):
        from projects.models import Chapter
        self.buy_and_apply()
        resume = Chapter.objects.get(project=self.project, title='Résumé')
        res = self.client.post(f'/projects/chapters/{resume.id}/generate_content/')
        self.assertEqual(res.status_code, 400)
        self.assertIn("Rédigez d'abord les chapitres", res.data['error'])
        self.create.assert_not_called()

    def test_preliminary_pages_are_not_generated(self):
        from projects.models import Chapter
        self.buy_and_apply()
        dedicace = Chapter.objects.get(project=self.project, title='Dédicace')
        self.assertEqual(self.client.post(f'/projects/chapters/{dedicace.id}/generate_content/').status_code, 400)


EXEMPLE_MARKDOWN = (
    "Je suis votre assistant académique. Je peux vous accompagner :\n\n"
    "- **Structurer votre travail** : plan, problématique\n"
    "- **Citations et références** : normes APA, etc. *(références à vérifier vous-même)*\n\n"
    "## Méthode\n1. **Introduction** générale [source à compléter]\n"
)


class CleanAITextTests(APITestCase):
    """Les réponses de l'IA ne doivent contenir aucun symbole Markdown (astérisques, dièses...)."""

    def test_markdown_removed_but_content_kept(self):
        out = services.clean_ai_text(EXEMPLE_MARKDOWN)
        for symbol in ('**', '*(', '## ', '- '):
            self.assertNotIn(symbol, out)
        self.assertIn('• Structurer votre travail : plan, problématique', out)
        self.assertIn('(références à vérifier vous-même)', out)
        self.assertIn('1. Introduction générale [source à compléter]', out)

    def test_ordinary_symbols_untouched(self):
        self.assertEqual(services.clean_ai_text('mon_fichier_final et 2*3 = 6'), 'mon_fichier_final et 2*3 = 6')

    @override_settings(AI_PROVIDER='openrouter', OPENAI_API_KEY='test-key', AI_MODEL='a/m', AI_FALLBACK_MODELS=[])
    def test_chat_answer_is_cleaned(self):
        services._openrouter_client.cache_clear()
        user = User.objects.create_user('propre@test.com', 'Motdepasse-Solide-2026', first_name='A', last_name='B')
        self.client.force_authenticate(user)
        with mock.patch.object(services, '_openrouter_client') as client:
            client.return_value.chat.completions.create.return_value = fake_chat_completion(EXEMPLE_MARKDOWN)
            res = self.client.post('/ai/chat/', {'message': 'Que sais-tu faire ?'})
        self.assertNotIn('**', res.data['response'])
        self.assertNotIn('##', res.data['response'])
