"""Tests des modèles de mémoire et du paiement Jɛmɛnipay (API simulée : aucun appel réel)."""
import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from projects.models import Chapter, Project
from users.models import User
from .covers import cover_data, render_cover_html
from .models import MemoirTemplate, TemplatePurchase

PASSWORD = 'Motdepasse-Solide-2026'
TX = '01m86jbwjce91t2dja8vgkf564'
CHECKOUT = {'status': 'Success', 'message': 'ok', 'data': {
    'checkout_url': f'https://jemeni.net/sandbox/pay/{TX}', 'expires_at': '2026-11-24T11:12:00+00:00',
    'transaction': {'id': TX, 'amount': 5000, 'state': 1, 'reference': 'JP-1'}}}


def payment_body(state, amount=5000, tx=TX):
    return {'status': 'Success', 'message': 'Etat de votre transaction',
            'data': {'id': tx, 'amount': amount, 'state': state, 'reference': 'JP-1'}}


def make_user(email, role='STUDENT'):
    return User.objects.create_user(email, PASSWORD, first_name='Awa', last_name='Diallo', role=role)


def fake_response(status, body):
    resp = mock.Mock(status_code=status)
    resp.json.return_value = body
    return resp


@override_settings(JEMENI_PUBLIC_KEY='pk_live_x', JEMENI_SECRET_KEY='sk_live_x', JEMENI_TOKEN='jeton',
                   JEMENI_API_URL='https://jemeni.test/api', JEMENI_WEBHOOK_SECRET='whsec_test',
                   FRONTEND_URL='http://localhost:5173')
class TemplatePurchaseTests(APITestCase):
    def setUp(self):
        self.user = make_user('etu@test.com')
        # Modèle payant au style « classique » (licence-classique est gratuit).
        self.template = MemoirTemplate.objects.get(slug='master-agronomie-environnement')
        self.client.force_authenticate(self.user)

    def purchase(self):
        with mock.patch('modeles.jemeni.requests.request', return_value=fake_response(200, CHECKOUT)) as req:
            res = self.client.post(f'/modeles/{self.template.slug}/purchase/')
        return res, req

    def test_catalog_first_template_free_others_at_5000_xof(self):
        res = self.client.get('/modeles/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 14)
        prices = {t['slug']: (t['price'], t['currency'], t['is_free']) for t in res.data}
        self.assertEqual(prices.pop('licence-classique'), ('0.00', 'XOF', True))
        self.assertEqual(set(prices.values()), {('5000.00', 'XOF', False)})
        self.assertEqual(len({t['cover_style'] for t in res.data}), 6)
        # Plan complet (conseils) réservé aux acheteurs ; titres visibles par tous.
        paid = next(t for t in res.data if not t['is_free'])
        self.assertIsNone(paid['structure'])
        self.assertTrue(paid['outline'])

    def test_free_template_is_available_to_everyone_without_payment(self):
        from projects.models import Project
        free = MemoirTemplate.objects.get(slug='licence-classique')
        data = next(t for t in self.client.get('/modeles/').data if t['slug'] == free.slug)
        self.assertTrue(data['owned'])
        self.assertTrue(data['structure'])  # conseils détaillés débloqués
        self.assertNotIn('APERÇU', self.client.get(f'/modeles/{free.slug}/cover/').data['html'])
        # Rien à payer : aucune page de paiement n'est créée.
        with mock.patch('modeles.jemeni.requests.request') as req:
            res = self.client.post(f'/modeles/{free.slug}/purchase/')
        self.assertEqual(res.status_code, 400)
        req.assert_not_called()
        self.assertFalse(TemplatePurchase.objects.exists())
        # Application directe à un mémoire.
        project = Project.objects.create(user=self.user, title='Mémoire', theme='Thème', desired_pages=40)
        res = self.client.post(f'/modeles/{free.slug}/apply/', {'project_id': project.id})
        self.assertEqual(res.status_code, 200)
        self.assertGreater(res.data['chapters_created'], 0)

    def test_cover_preview_is_watermarked_until_purchased(self):
        res = self.client.get(f'/modeles/{self.template.slug}/cover/')
        self.assertIn('APERÇU', res.data['html'])
        self.assertIn('République du Mali', res.data['html'])

    def test_purchase_creates_signed_checkout(self):
        res, req = self.purchase()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['checkout_url'], CHECKOUT['data']['checkout_url'])
        method, url = req.call_args.args
        headers, body = req.call_args.kwargs['headers'], req.call_args.kwargs['data'].decode()
        self.assertEqual((method, url), ('POST', 'https://jemeni.test/api/live/payments/checkout'))
        # Signature : HMAC-SHA512(SK + AK + MÉTHODE + URL + CORPS + TIMESTAMP), clé = SK
        message = f"sk_live_xpk_live_xPOST{url}{body}{headers['auth-timestamp']}"
        self.assertEqual(headers['auth-signature'],
                         hmac.new(b'sk_live_x', message.encode(), hashlib.sha512).hexdigest())
        self.assertEqual((headers['auth-apiKey'], headers['auth-token']), ('pk_live_x', 'jeton'))
        self.assertNotIn('sandbox', headers)
        self.assertNotIn('sk_live_x', str(headers))  # la clé secrète n'est jamais envoyée
        payload = json.loads(body)
        purchase = TemplatePurchase.objects.get()
        self.assertEqual((payload['amount'], payload['country_code']), (5000, 'ml'))
        self.assertEqual(payload['return_url'], f'http://localhost:5173/modeles?achat={purchase.id}')
        self.assertEqual(payload['metadata']['purchase_id'], purchase.id)
        self.assertEqual((purchase.provider, purchase.checkout_session_id), ('jemeni', TX))

    @override_settings(JEMENI_PUBLIC_KEY='pk_test_x', JEMENI_SECRET_KEY='sk_test_x')
    def test_test_keys_use_sandbox(self):
        _, req = self.purchase()
        self.assertEqual(req.call_args.args[1], 'https://jemeni.test/api/sandbox/payments/checkout')
        self.assertEqual(req.call_args.kwargs['headers']['sandbox'], 'true')
        self.assertEqual(TemplatePurchase.objects.get().provider, 'jemeni_test')

    def test_simulated_payments_unlock_templates_only_with_test_keys(self):
        TemplatePurchase.objects.create(user=self.user, template=self.template, amount=5000, status='PAID',
                                        provider='jemeni_test')
        self.assertFalse(self.template.is_owned_by(self.user))  # clés réelles : un paiement simulé ne compte pas
        mine = next(t for t in self.client.get('/modeles/').data if t['slug'] == self.template.slug)
        self.assertFalse(mine['owned'])
        with override_settings(JEMENI_PUBLIC_KEY='pk_test_x'):
            self.assertTrue(self.template.is_owned_by(self.user))

    @override_settings(JEMENI_PUBLIC_KEY='pk_test_x', JEMENI_ALLOW_SANDBOX=False)
    def test_test_keys_are_refused_in_production(self):
        """Production avec des clés de test : aucun paiement, aucun modèle débloqué par un paiement simulé."""
        done = TemplatePurchase.objects.create(user=self.user, template=self.template, amount=5000, status='PAID',
                                               provider='jemeni_test')
        self.assertFalse(self.template.is_owned_by(self.user))
        done.status, done.checkout_session_id, done.checkout_url = 'PENDING', TX, 'https://jemeni.net/sandbox/pay/x'
        done.save()
        with mock.patch('modeles.jemeni.requests.request') as req:
            res = self.client.post(f'/modeles/{self.template.slug}/purchase/')
            self.assertEqual(res.status_code, 503)
            res = self.client.post(f'/modeles/achats/{done.id}/verify/')
            self.assertEqual((res.data['status'], res.data['checkout_url']), ('PENDING', ''))
        req.assert_not_called()

    def test_old_saspay_purchases(self):
        """Achats SasPay : les payés restent acquis, les liens en attente ne sont plus proposés ni interrogés."""
        old = TemplatePurchase.objects.create(user=self.user, template=self.template, amount=5000, provider='saspay',
                                              checkout_session_id='sess-1', checkout_url='https://pay.saspay.me/c/abc')
        with mock.patch('modeles.jemeni.requests.request') as req:
            res = self.client.post(f'/modeles/achats/{old.id}/verify/')
        req.assert_not_called()
        self.assertEqual((res.data['status'], res.data['checkout_url']), ('PENDING', ''))
        res, _ = self.purchase()
        self.assertEqual(res.status_code, 201)  # nouvelle page Jɛmɛnipay, pas l'ancien lien
        TemplatePurchase.objects.filter(pk=old.pk).update(status='PAID')
        self.assertTrue(self.template.is_owned_by(self.user))

    def test_expired_checkout_is_not_reused(self):
        self.purchase()
        TemplatePurchase.objects.update(created_at=timezone.now() - timedelta(minutes=40))
        self.assertEqual(self.client.get('/modeles/achats/').data[0]['checkout_url'], '')
        res, req = self.purchase()
        self.assertEqual(res.status_code, 201)
        req.assert_called_once()

    def test_second_click_reuses_pending_session(self):
        self.purchase()
        res, req = self.purchase()
        self.assertEqual(res.status_code, 200)
        req.assert_not_called()
        self.assertEqual(TemplatePurchase.objects.count(), 1)

    def test_provider_error_is_reported(self):
        body = {'status': 'Error', 'message': 'Signature invalide', 'data': None}
        with mock.patch('modeles.jemeni.requests.request', return_value=fake_response(403, body)):
            res = self.client.post(f'/modeles/{self.template.slug}/purchase/')
        self.assertEqual(res.status_code, 503)
        self.assertEqual(TemplatePurchase.objects.get().status, 'FAILED')

    def _verify(self, body, status=200):
        purchase = TemplatePurchase.objects.get()
        with mock.patch('modeles.jemeni.requests.request', return_value=fake_response(status, body)) as req:
            res = self.client.post(f'/modeles/achats/{purchase.id}/verify/')
        self.assertEqual(req.call_args.args, ('GET', f'https://jemeni.test/api/live/payments/{TX}'))
        return res

    def test_verify_marks_paid_only_when_completed(self):
        self.purchase()
        for state in (0, 1):
            self.assertEqual(self._verify(payment_body(state)).data['status'], 'PENDING')
        res = self._verify(payment_body(2, amount='5000.00'))
        self.assertEqual(res.data['status'], 'PAID')
        self.assertTrue(self.template.is_owned_by(self.user))
        purchase = TemplatePurchase.objects.get()
        self.assertEqual((purchase.transaction_id, purchase.amount_charged), (TX, Decimal('5000.00')))

    def test_refused_payment_then_late_confirmation(self):
        self.purchase()
        self.assertEqual(self._verify(payment_body(3)).data['status'], 'FAILED')
        self.assertFalse(self.template.is_owned_by(self.user))
        # Un paiement finalement confirmé est toujours enregistré.
        self.assertEqual(self._verify(payment_body(2)).data['status'], 'PAID')

    def test_abandoned_payment_is_cancelled(self):
        self.purchase()
        TemplatePurchase.objects.update(created_at=timezone.now() - timedelta(hours=3))
        self.assertEqual(self._verify(payment_body(1)).data['status'], 'CANCELLED')

    def test_underpaid_or_foreign_transaction_is_not_accepted(self):
        self.purchase()
        self.assertEqual(self._verify(payment_body(2, amount=100)).data['status'], 'PENDING')
        self.assertEqual(self._verify(payment_body(2, tx='autre')).data['status'], 'PENDING')
        self.assertFalse(self.template.is_owned_by(self.user))

    def test_unknown_transaction_error_keeps_purchase_pending(self):
        self.purchase()
        res = self._verify({'status': 'Error', 'message': 'No query results', 'data': []}, status=500)
        self.assertEqual(res.status_code, 502)
        self.assertEqual(TemplatePurchase.objects.get().status, 'PENDING')

    def test_cannot_verify_someone_elses_purchase(self):
        self.purchase()
        self.client.force_authenticate(make_user('autre@test.com'))
        purchase = TemplatePurchase.objects.get()
        self.assertEqual(self.client.post(f'/modeles/achats/{purchase.id}/verify/').status_code, 404)

    def test_apply_requires_purchase_then_creates_plan(self):
        project = Project.objects.create(user=self.user, title='Mon mémoire', level='LICENCE')
        res = self.client.post(f'/modeles/{self.template.slug}/apply/', {'project_id': project.id})
        self.assertEqual(res.status_code, 402)

        TemplatePurchase.objects.create(user=self.user, template=self.template, amount=5000, status='PAID')
        res = self.client.post(f'/modeles/{self.template.slug}/apply/', {'project_id': project.id})
        self.assertEqual(res.status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.template, self.template)
        self.assertEqual(project.status, 'IN_PROGRESS')
        self.assertTrue(Chapter.objects.filter(project=project, title='Introduction générale').exists())
        self.assertTrue(Chapter.objects.filter(project=project, parent__isnull=False, content__contains='Conseil').exists())

    def test_template_cannot_be_set_without_paying(self):
        project = Project.objects.create(user=self.user, title='M')
        self.client.patch(f'/projects/projects/{project.id}/', {'template': self.template.id})
        project.refresh_from_db()
        self.assertIsNone(project.template)

    def test_export_includes_cover_of_purchased_template(self):
        TemplatePurchase.objects.create(user=self.user, template=self.template, amount=5000, status='PAID')
        project = Project.objects.create(user=self.user, title='Mémoire avec garde', university='USTTB',
                                         template=self.template)
        res = self.client.post(f'/projects/projects/{project.id}/export/', {'format': 'html'}, format='json')
        body = res.content.decode()
        self.assertIn('class="page"', body)
        self.assertIn('Présenté par', body)
        self.assertNotIn('APERÇU', body)
        for fmt in ('pdf', 'docx'):
            res = self.client.post(f'/projects/projects/{project.id}/export/', {'format': fmt}, format='json')
            self.assertEqual(res.status_code, 200, fmt)

    def test_word_and_pdf_use_the_template_cover_design(self):
        """Word et PDF reprennent la page de garde du modèle (même design que l'aperçu), pour les 6 styles."""
        from io import BytesIO

        from docx import Document
        from PyPDF2 import PdfReader
        TemplatePurchase.objects.create(user=self.user, template=self.template, amount=5000, status='PAID')
        project = Project.objects.create(user=self.user, title="Gestion de l'eau à Kayes", university='USTTB',
                                         academic_year='2025-2026', city='Bamako', template=self.template)
        Chapter.objects.create(project=project, title='Introduction générale', type='chapter', order=1, content='Texte.')

        def export(fmt):
            res = self.client.post(f'/projects/projects/{project.id}/export/', {'format': fmt}, format='json')
            self.assertEqual(res.status_code, 200)
            return b''.join(res.streaming_content) if hasattr(res, 'streaming_content') else res.content

        for style in ('classique', 'moderne', 'elegant', 'these', 'minimaliste', 'institutionnel'):
            self.template.cover_style = style
            self.template.accent_color = '#7c2d12'
            self.template.save()
            with self.subTest(style=style):
                doc = Document(BytesIO(export('docx')))
                cover_xml = doc.sections[0]._sectPr.xml
                body = doc.element.body.xml
                first_section_text = []
                for block in doc.element.body.iterchildren():
                    first_section_text.append(''.join(block.itertext()))
                    if block.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr') is not None:
                        break
                cover_text = ' '.join(first_section_text)
                self.assertIn("GESTION DE L'EAU À KAYES", cover_text.upper())  # l'élégant l'affiche en petites capitales
                self.assertIn('PRÉSENTÉ PAR', cover_text)
                self.assertIn('Année universitaire 2025-2026', cover_text)
                self.assertIn('7C2D12', body)  # couleur du modèle
                if style == 'elegant':
                    self.assertIn('w:pgBorders', cover_xml)  # double cadre de page
                self.assertNotIn('PAGE', doc.sections[0].footer._element.xml)  # garde non numérotée

                first_page = PdfReader(BytesIO(export('pdf'))).pages[0].extract_text()
                self.assertIn('PRÉSENTÉ PAR', first_page)
                self.assertIn('KAYES', first_page.upper())

    def _webhook(self, body, secret='whsec_test'):
        raw = json.dumps(body).encode()
        sig = hmac.new(secret.encode(), raw, hashlib.sha512).hexdigest()
        return self.client.generic('POST', '/modeles/webhook/jemeni/', raw, content_type='application/json',
                                   HTTP_X_JEMENI_SIGNATURE=sig)

    def test_webhook_rejects_bad_signature(self):
        event = {'event': 'payment.success', 'data': {'transaction_id': TX}}
        self.assertEqual(self._webhook(event, secret='wrong').status_code, 401)
        with override_settings(JEMENI_WEBHOOK_SECRET=''):  # non configuré : tout est refusé
            self.assertEqual(self._webhook(event, secret='').status_code, 401)

    def test_webhook_confirms_purchase_through_api(self):
        self.purchase()
        event = {'event': 'payment.success', 'data': {'transaction_id': TX, 'state': 2, 'amount': '5000'}}
        # Le contenu du webhook n'est pas cru : l'API dit « en attente », l'achat reste en attente.
        with mock.patch('modeles.jemeni.requests.request', return_value=fake_response(200, payment_body(1))):
            self.assertEqual(self._webhook(event).status_code, 200)
        self.assertEqual(TemplatePurchase.objects.get().status, 'PENDING')
        with mock.patch('modeles.jemeni.requests.request', return_value=fake_response(200, payment_body(2))):
            self.assertEqual(self._webhook(event).status_code, 200)
        self.assertEqual(TemplatePurchase.objects.get().status, 'PAID')
        # Nouvel envoi du même événement : aucun effet, aucun appel.
        with mock.patch('modeles.jemeni.requests.request') as req:
            self.assertEqual(self._webhook(event).status_code, 200)
        req.assert_not_called()


class CoverRenderingTests(APITestCase):
    def test_every_style_renders_and_escapes(self):
        for template in MemoirTemplate.objects.all():
            data = cover_data(template)
            data['title'] = '<script>alert(1)</script>'
            html = render_cover_html(template, data)
            self.assertIn('&lt;script&gt;', html, template.slug)
            self.assertNotIn('<script>', html, template.slug)
