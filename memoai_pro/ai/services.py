"""Appels IA pour les fonctions du cahier des charges (§3.5, §3.7).

Fournisseur choisi par AI_PROVIDER : "openrouter" (API compatible OpenAI) ou "anthropic" (API Claude)."""
import json
import logging
import re
import time
from functools import lru_cache

import anthropic
import openai
from django.conf import settings
from django.core.cache import cache

from projects.models import Project

logger = logging.getLogger(__name__)

# Modèles qui acceptent le repli automatique côté serveur en cas de refus.
FALLBACK_MODELS = {'claude-opus-5-5', 'claude-opus-5', 'claude-fable-5-1', 'claude-sonnet-5-5'}

ACADEMIC_SYSTEM = (
    "Vous êtes l'assistant académique de MemoAI Pro. Vous aidez des étudiants à rédiger "
    "leur mémoire ou leur thèse universitaire. Répondez en français sauf demande contraire, "
    "dans un registre académique clair. N'inventez jamais de références : si vous citez un "
    "ouvrage ou un article, signalez qu'il doit être vérifié par l'étudiant."
)


class AIError(Exception):
    """Erreur IA à présenter telle quelle à l'utilisateur."""

    def __init__(self, message, status=502, retry_after=None):
        super().__init__(message)
        self.status = status
        # Délai conseillé (secondes) avant de réessayer, renvoyé dans l'en-tête Retry-After.
        self.retry_after = retry_after


def translate_openrouter_error(e):
    """Convertit une erreur OpenRouter en AIError présentable à l'utilisateur."""
    if isinstance(e, openai.APIStatusError):
        if e.status_code == 402:
            return AIError("Le service IA est temporairement indisponible (crédit OpenRouter épuisé). Contactez l'administrateur.", 503)
        if e.status_code in (401, 403):
            return AIError("Le service IA est mal configuré (clé API invalide). Contactez l'administrateur.", 503)
        if e.status_code == 429:
            return AIError('Trop de requêtes IA en peu de temps. Réessayez dans un instant.', 429)
        if e.status_code >= 500:
            return AIError('Le service IA est surchargé. Réessayez dans quelques instants.', 503)
        return AIError('La requête IA a été rejetée. Réessayez avec un texte plus court.', 502)
    if isinstance(e, openai.APIConnectionError):
        return AIError('Le service IA est injoignable. Réessayez plus tard.', 502)
    return AIError("Erreur inattendue du service IA.", 502)


def translate_api_error(e):
    """Convertit une erreur de l'API Claude en AIError présentable à l'utilisateur."""
    if isinstance(e, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return AIError("Le service IA est mal configuré (clé API invalide). Contactez l'administrateur.", 503)
    if isinstance(e, anthropic.RateLimitError):
        return AIError('Trop de requêtes IA en peu de temps. Réessayez dans un instant.', 429)
    if isinstance(e, anthropic.APIStatusError):
        # Un solde insuffisant arrive en 402 (billing_error) ou en 400 dont seul
        # le message mentionne le crédit : on vérifie les deux.
        if e.status_code == 402 or e.type == 'billing_error' or 'credit balance' in str(e.message).lower():
            return AIError("Le service IA est temporairement indisponible (crédit API épuisé). Contactez l'administrateur.", 503)
        if e.status_code >= 500:
            return AIError('Le service IA est surchargé. Réessayez dans quelques instants.', 503)
        return AIError('La requête IA a été rejetée. Réessayez avec un texte plus court.', 502)
    if isinstance(e, anthropic.APIConnectionError):
        return AIError('Le service IA est injoignable. Réessayez plus tard.', 502)
    return AIError("Erreur inattendue du service IA.", 502)


@lru_cache(maxsize=1)
def _client():
    if not settings.ANTHROPIC_API_KEY:
        raise AIError("Le service IA n'est pas configuré (ANTHROPIC_API_KEY manquante).", 503)
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


@lru_cache(maxsize=1)
def _openrouter_client():
    if not settings.OPENAI_API_KEY:
        raise AIError("Le service IA n'est pas configuré (OPENAI_API_KEY manquante).", 503)
    # max_retries=1 : en cas de saturation, mieux vaut passer vite au modèle suivant
    # que d'attendre les ré-essais du SDK sur le même modèle.
    return openai.OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL, max_retries=1, timeout=120)


def _extract_json(text):
    """Isole l'objet JSON d'une réponse (le modèle peut l'entourer de texte ou de ```)."""
    start, end = text.find('{'), text.rfind('}')
    try:
        if start == -1 or end < start:
            raise ValueError('aucun objet JSON')
        json.loads(text[start:end + 1])
    except ValueError:
        logger.error('Réponse IA non JSON : %.300s', text)
        raise AIError("La réponse de l'IA est mal formée. Réessayez.", 502)
    return text[start:end + 1]


# Erreurs pour lesquelles on essaie le modèle suivant : saturation (429), panne du fournisseur (5xx),
# délai dépassé (408) ou modèle retiré du catalogue OpenRouter (404).
RETRYABLE_STATUSES = {404, 408, 429, 500, 502, 503, 504}


# Un modèle qui vient de répondre 429 est mis en pause : on ne gaspille pas le quota
# quotidien des modèles gratuits OpenRouter (50 requêtes/jour) à le réinterroger aussitôt.
MODEL_COOLDOWN_SECONDS = 90
DAILY_QUOTA_KEY = 'ai:openrouter:daily-quota-reached'
DAILY_QUOTA_MESSAGE = (
    "Le quota quotidien du service IA gratuit est atteint. Réessayez plus tard "
    "(l'administrateur peut ajouter du crédit OpenRouter pour lever cette limite)."
)


def _cooldown_key(model):
    return f'ai:openrouter:cooldown:{model}'


def _openrouter_models():
    """Modèle principal puis modèles de secours, sans doublon. Les modèles saturés
    récemment passent en dernier : ils ne sont essayés que si tous les autres échouent."""
    seen, models = set(), []
    for model in [settings.AI_MODEL, *settings.AI_FALLBACK_MODELS]:
        if model and model not in seen:
            seen.add(model)
            models.append(model)
    cooling = cache.get_many([_cooldown_key(m) for m in models])
    return sorted(models, key=lambda m: _cooldown_key(m) in cooling)


def _is_daily_quota_error(e):
    """OpenRouter signale l'épuisement du quota gratuit par un 429 « free-models-per-day »."""
    text = f'{e.message} {e.body}'.lower()
    return 'per-day' in text or 'per day' in text


def _seconds_until_reset(e, default=3600):
    """Délai avant la remise à zéro du quota (en-tête X-RateLimit-Reset, en millisecondes)."""
    try:
        reset_ms = int(e.response.headers.get('X-RateLimit-Reset'))
    except (TypeError, ValueError, AttributeError):
        return default
    return max(60, min(int(reset_ms / 1000 - time.time()), 24 * 3600))


def _ask_openrouter(prompt, system, schema, max_tokens, allow_truncated=False):
    """Interroge les modèles un par un : si l'un est saturé ou indisponible, on passe au suivant."""
    if schema:
        system += (
            "\n\nRépondez UNIQUEMENT avec un objet JSON valide, sans texte autour, "
            f"conforme à ce schéma JSON :\n{json.dumps(schema, ensure_ascii=False)}"
        )
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}]
    quota_reset_at = cache.get(DAILY_QUOTA_KEY)
    if quota_reset_at:
        raise AIError(DAILY_QUOTA_MESSAGE, 429, retry_after=max(60, int(quota_reset_at - time.time())))

    models = _openrouter_models()
    try:
        return _try_openrouter_models(models, messages, schema, max_tokens, allow_truncated)
    except _AllSaturated as first_failure:
        # Saturation passagère côté fournisseur (« retry shortly ») : une seconde chance
        # après une courte pause, sur le premier modèle saturé uniquement.
        time.sleep(settings.AI_SATURATION_RETRY_DELAY)
        try:
            return _try_openrouter_models(first_failure.models[:1], messages, schema, max_tokens, allow_truncated)
        except _AllSaturated:
            raise AIError("Les modèles IA sont saturés en ce moment (forte demande sur les modèles gratuits). "
                          "Réessayez dans une minute.", 429, retry_after=60) from None


class _AllSaturated(Exception):
    """Tous les modèles ont échoué et au moins un était saturé (429)."""

    def __init__(self, models):
        super().__init__('saturated')
        self.models = models


def _try_openrouter_models(models, messages, schema, max_tokens, allow_truncated):
    last_error = None
    saturated = []
    for model in models:
        # Les modèles gratuits ne réservent pas de crédit : on laisse de la place
        # aux modèles qui « réfléchissent » avant de répondre.
        tokens = max(max_tokens, 8000) if model.endswith(':free') else max_tokens
        try:
            response = _openrouter_client().chat.completions.create(
                model=model, messages=messages, temperature=0.4, max_tokens=tokens,
            )
        except openai.APIStatusError as e:
            if e.status_code == 429 and _is_daily_quota_error(e):
                delay = _seconds_until_reset(e)
                logger.error('OpenRouter: quota quotidien des modèles gratuits atteint (remise à zéro dans %ss).', delay)
                cache.set(DAILY_QUOTA_KEY, time.time() + delay, delay)
                raise AIError(DAILY_QUOTA_MESSAGE, 429, retry_after=delay) from e
            if e.status_code in RETRYABLE_STATUSES:
                logger.warning('OpenRouter: %s indisponible (%s), modèle suivant.', model, e.status_code)
                if e.status_code == 429:
                    saturated.append(model)
                    cache.set(_cooldown_key(model), True, MODEL_COOLDOWN_SECONDS)
                last_error = e
                continue
            logger.error('OpenRouter API error (%s): %s', model, e)
            raise translate_openrouter_error(e) from e
        except openai.APIConnectionError as e:
            logger.warning('OpenRouter: %s injoignable, modèle suivant.', model)
            last_error = e
            continue

        choice = response.choices[0] if getattr(response, 'choices', None) else None
        text = (choice.message.content or '').strip() if choice else ''
        if not text:
            # Réponse vide ou erreur du fournisseur dans une réponse 200.
            logger.warning('OpenRouter: réponse vide de %s, modèle suivant.', model)
            last_error = AIError("Le modèle IA n'a pas répondu. Réessayez dans un instant.", 502)
            continue
        if choice.finish_reason == 'length' and not allow_truncated:
            last_error = AIError("La réponse de l'IA est trop longue. Réduisez la taille du texte envoyé.", 422)
            if schema:  # JSON tronqué : inutilisable, on tente le modèle suivant
                logger.warning('OpenRouter: réponse JSON tronquée de %s, modèle suivant.', model)
                continue
            raise last_error
        if not schema:
            return text
        try:
            return _extract_json(text)
        except AIError as e:
            last_error = e
            continue

    if saturated:
        raise _AllSaturated(saturated)
    if isinstance(last_error, AIError):
        raise last_error
    raise translate_openrouter_error(last_error) if last_error else AIError("Aucun modèle IA n'est configuré.", 503)


def _ask(prompt, *, system=ACADEMIC_SYSTEM, effort=None, schema=None, openrouter_max_tokens=1500, allow_truncated=False):
    """Envoie un message au fournisseur IA configuré et renvoie le texte de la réponse.
    `openrouter_max_tokens` reste bas : OpenRouter réserve ce plafond sur le crédit à chaque appel."""
    if settings.AI_PROVIDER == 'openrouter':
        return _ask_openrouter(prompt, system, schema, openrouter_max_tokens, allow_truncated)

    model = settings.AI_MODEL
    output_config = {}
    if effort:
        output_config['effort'] = effort
    if schema:
        output_config['format'] = {'type': 'json_schema', 'schema': schema}

    kwargs = {
        'model': model,
        'max_tokens': 16000,
        'system': system,
        'messages': [{'role': 'user', 'content': prompt}],
    }
    if output_config:
        kwargs['output_config'] = output_config
    if model in FALLBACK_MODELS:
        kwargs['betas'] = ['server-side-fallback-2026-07-01']
        kwargs['fallbacks'] = 'default'

    try:
        response = _client().beta.messages.create(**kwargs)
    except anthropic.APIError as e:
        logger.error('Claude API error: %s', e)
        raise translate_api_error(e) from e

    if response.stop_reason == 'refusal':
        raise AIError("L'IA a refusé de traiter cette demande. Reformulez votre texte.", 422)
    if response.stop_reason == 'max_tokens' and not allow_truncated:
        raise AIError('La réponse de l\'IA est trop longue. Réduisez la taille du texte envoyé.', 422)
    return ''.join(block.text for block in response.content if block.type == 'text')


CHAPTER_MARKER = re.compile(r'^\s*#{2,4}\s*(INTRODUCTION[^\n]*|SECTION\s+(\d+)[^\n]*)$', re.IGNORECASE | re.MULTILINE)


def parse_chapter_text(text, section_count):
    """Découpe la réponse de write_chapter selon les lignes « ### INTRODUCTION » / « ### SECTION n »."""
    result = {'intro': '', 'sections': {}}
    matches = list(CHAPTER_MARKER.finditer(text))
    if not matches:
        if section_count == 0:
            result['intro'] = text.strip()
            return result
        raise AIError("La réponse de l'IA n'a pas le format attendu. Réessayez.", 502)
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[match.end():end].strip()
        if not body:
            continue
        if match.group(2):
            number = int(match.group(2))
            if 1 <= number <= section_count:
                result['sections'][number] = body
        else:
            result['intro'] = body
    return result


def _str_list(description):
    return {'type': 'array', 'description': description, 'items': {'type': 'string'}}


PLAN_SCHEMA = {
    'type': 'object',
    'properties': {
        'chapters': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'},
                    'order': {'type': 'integer'},
                    'sections': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'title': {'type': 'string'},
                                'subsections': _str_list('Titres des sous-sections'),
                            },
                            'required': ['title', 'subsections'],
                            'additionalProperties': False,
                        },
                    },
                },
                'required': ['title', 'order', 'sections'],
                'additionalProperties': False,
            },
        },
        'figures': _str_list('Figures, graphiques et illustrations recommandés'),
        'tables': _str_list('Tableaux recommandés'),
        'references': _str_list('Références suggérées, à vérifier par l\'étudiant'),
        'appendices': _str_list('Annexes suggérées (questionnaires, guides d\'entretien...)'),
        'glossary': _str_list('Termes du glossaire'),
    },
    'required': ['chapters', 'figures', 'tables', 'references', 'appendices', 'glossary'],
    'additionalProperties': False,
}

VERIFY_SCHEMA = {
    'type': 'object',
    'properties': {
        'score': {'type': 'integer', 'description': 'Qualité scientifique globale de 0 à 100'},
        'summary': {'type': 'string'},
        'issues': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'type': {'type': 'string', 'enum': ['incoherence', 'affirmation_sans_source', 'imprecision', 'style']},
                    'excerpt': {'type': 'string', 'description': 'Passage concerné, cité mot pour mot'},
                    'explanation': {'type': 'string'},
                    'suggestion': {'type': 'string'},
                },
                'required': ['type', 'excerpt', 'explanation', 'suggestion'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['score', 'summary', 'issues'],
    'additionalProperties': False,
}

REFORMULATION_STYLES = {
    'academic': 'un style académique soutenu',
    'simple': 'un style plus simple et plus clair, sans perdre la précision',
    'formal': 'un style formel et concis',
}

LANGUAGES = {'fr': 'français', 'en': 'anglais', 'es': 'espagnol', 'ar': 'arabe', 'pt': 'portugais', 'de': 'allemand'}


class AIService:
    @staticmethod
    def generate_plan(theme, context='', guide=''):
        """Plan complet du mémoire (§3.5). Renvoie une chaîne JSON conforme à PLAN_SCHEMA.
        `guide` : structure du modèle de mémoire acheté, que le plan doit respecter."""
        prompt = (
            f"Générez le plan détaillé d'un mémoire universitaire sur le thème suivant :\n"
            f"<theme>{theme}</theme>\n"
        )
        if context:
            prompt += f"\n<contexte>{context}</contexte>\n"
        if guide:
            prompt += (
                "\nRespectez la structure type suivante (organisation et logique des chapitres), "
                "en remplaçant les titres génériques par des titres précis et propres au thème :\n"
                f"<structure_type>{guide}</structure_type>\n"
            )
        prompt += (
            "\nLe plan comprend une introduction générale, plusieurs chapitres avec sections et "
            "sous-sections, une conclusion générale, ainsi que les figures, tableaux, références, "
            "annexes et termes de glossaire recommandés. Soyez concis : 3 à 6 chapitres, 2 à 4 sections "
            "par chapitre, 0 à 3 sous-sections par section, et au plus 5 éléments dans chacune des listes "
            "figures, tableaux, références, annexes et glossaire. N'incluez pas les pages liminaires "
            "(dédicace, remerciements, résumé), ni la bibliographie, ni les annexes dans les chapitres."
        )
        return _ask(prompt, schema=PLAN_SCHEMA, openrouter_max_tokens=3000)

    @staticmethod
    def write_chapter(context, chapter_title, chapter_guidance, sections, words_per_section, language='fr'):
        """Rédige un chapitre : introduction du chapitre puis chaque section.
        `sections` : [(titre, consigne)]. Renvoie {'intro': str, 'sections': {numéro: str}}."""
        lang = LANGUAGES.get(language, 'français')
        prompt = (
            f"Rédigez en {lang} le contenu du chapitre suivant d'un mémoire universitaire.\n"
            f"<memoire>{context}</memoire>\n"
            f"<chapitre>{chapter_title}</chapitre>\n"
        )
        if chapter_guidance:
            prompt += f"<consigne_chapitre>{chapter_guidance}</consigne_chapitre>\n"
        prompt += (
            "\nRespectez EXACTEMENT ce format, avec ces lignes de titre et rien d'autre autour :\n"
            "### INTRODUCTION DU CHAPITRE\n(un paragraphe de 80 à 150 mots qui annonce le chapitre)\n"
        )
        for i, (title, hint) in enumerate(sections, start=1):
            prompt += f"### SECTION {i} — {title}" + (f" (consigne : {hint})" if hint else '') + "\n"
            prompt += f"(environ {words_per_section} mots)\n"
        prompt += (
            "\nRègles : style académique, paragraphes développés et argumentés, pas de listes à puces "
            "sauf si nécessaire, pas de titre markdown supplémentaire. N'inventez jamais de références "
            "bibliographiques ni de chiffres précis : quand une source ou une donnée est nécessaire, écrivez "
            "[source à compléter] ou [donnée à vérifier]."
        )
        text = _ask(prompt, openrouter_max_tokens=6000, allow_truncated=True)
        return parse_chapter_text(text, len(sections))

    @staticmethod
    def chat(message, project_id, user):
        system = ACADEMIC_SYSTEM
        if project_id:
            project = Project.objects.filter(id=project_id, user=user).first()
            if project:
                system += f"\n\nL'étudiant travaille sur un mémoire de niveau {project.level} intitulé « {project.title} »"
                system += f", sur le thème : {project.theme}." if project.theme else '.'
        return _ask(message, system=system)

    @staticmethod
    def verify(content):
        """IA scientifique : incohérences et affirmations sans source (§3.7)."""
        return json.loads(_ask(
            "Relisez ce passage de mémoire comme un relecteur scientifique exigeant. Relevez les "
            "incohérences, les affirmations qui nécessiteraient une source, les imprécisions et "
            "les problèmes de style académique. Si le texte ne pose pas de problème, renvoyez une "
            f"liste vide.\n\n<texte>{content}</texte>",
            effort='high',
            schema=VERIFY_SCHEMA,
            openrouter_max_tokens=2000,
        ))

    @staticmethod
    def reformulate(text, style='academic'):
        style_label = REFORMULATION_STYLES.get(style, REFORMULATION_STYLES['academic'])
        return _ask(
            f"Reformulez le texte suivant dans {style_label}, en conservant son sens et sa langue. "
            f"Renvoyez uniquement le texte reformulé.\n\n<texte>{text}</texte>",
            effort='low',
        )

    @staticmethod
    def summarize(text):
        return _ask(
            "Résumez le texte suivant en un paragraphe académique qui conserve les idées clés. "
            f"Renvoyez uniquement le résumé.\n\n<texte>{text}</texte>",
            effort='low',
        )

    @staticmethod
    def translate(text, target_lang='en'):
        language = LANGUAGES.get(target_lang, target_lang)
        return _ask(
            f"Traduisez le texte suivant en {language}, dans un registre académique. "
            f"Renvoyez uniquement la traduction.\n\n<texte>{text}</texte>",
            effort='low',
        )
