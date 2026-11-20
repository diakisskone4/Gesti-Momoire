"""Tests des modèles de mémoire et du paiement SasPay (API simulée : aucun appel réel)."""
import hashlib
import hmac
import json
import time
from decimal import Decimal
from unittest import mock

from django.test import override_settings
from rest_framework.test import APITestCase

from projects.models import Chapter, Project
from users.models import User
from .covers import cover_data, render_cover_html
from .models import MemoirTemplate, TemplatePurchase

PASSWORD = 'Motdepasse-Solide-2026'
SESSION = {'id': 'sess-uuid-1', 'checkout_url': 'https://pay.saspay.me/c/abc', 'status': 'PENDING'}


def make_user(email, role='STUDENT'):
    return User.objects.create_user(email, PASSWORD, first_name='Awa', last_name='Diallo', role=role)


def fake_response(status, body):
    resp = mock.Mock(status_code=status)
    resp.json.return_value = body
    return resp


@override_settings(SASPAY_SECRET_KEY='sk_test_x', SASPAY_API_URL='https://sandbox.test/api/v1',
                   SASPAY_WEBHOOK_SECRET='whsec_test', FRONTEND_URL='http://localhost:5173')
class TemplatePurchaseTests(APITestCase):
    def setUp(self):
        self.user = make_user('etu@test.com')
        # Modèle payant au style « classique » (licence-classique est gratuit).
        self.template = MemoirTemplate.objects.get(slug='master-agronomie-environnement')
        self.client.force_authenticate(self.user)

    def purchase(self):
        with mock.patch('modeles.saspay.requests.request', return_value=fake_response(201, SESSION)) as req:
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
        # Rien à payer : aucune session SasPay n'est créée.
        with mock.patch('modeles.saspay.requests.request') as req:
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

    def test_purchase_creates_saspay_checkout_session(self):
        res, req = self.purchase()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['checkout_url'], SESSION['checkout_url'])
        method, url = req.call_args.args
        payload = req.call_args.kwargs['json']
        self.assertEqual((method, url), ('POST', 'https://sandbox.test/api/v1/checkout-sessions/'))
        self.assertEqual(req.call_args.kwargs['headers']['Authorization'], 'Bearer sk_test_x')
        self.assertEqual(payload['amount'], '5000.00')
        self.assertEqual(payload['currency'], 'XOF')
        self.assertEqual(payload['customer_email'], 'etu@test.com')
        purchase = TemplatePurchase.objects.get()
        self.assertEqual(payload['return_url'], f'http://localhost:5173/modeles?achat={purchase.id}')
        self.assertEqual(payload['metadata']['purchase_id'], purchase.id)

    def test_second_click_reuses_pending_session(self):
        self.purchase()
        res, req = self.purchase()
        self.assertEqual(res.status_code, 200)
        req.assert_not_called()
        self.assertEqual(TemplatePurchase.objects.count(), 1)

    def test_saspay_error_is_reported(self):
        with mock.patch('modeles.saspay.requests.request', return_value=fake_response(401, {'success': False})):
            res = self.client.post(f'/modeles/{self.template.slug}/purchase/')
        self.assertEqual(res.status_code, 503)
        self.assertEqual(TemplatePurchase.objects.get().status, 'FAILED')

    def _verify(self, session, payment=None):
        responses = [fake_response(200, session)] + ([fake_response(200, payment)] if payment else [])
        purchase = TemplatePurchase.objects.get()
        with mock.patch('modeles.saspay.requests.request', side_effect=responses):
            return self.client.post(f'/modeles/achats/{purchase.id}/verify/')

    def test_verify_marks_paid_only_after_payment_check(self):
        self.purchase()
        res = self._verify({'status': 'PENDING', 'transaction_id': None, 'transaction_status': None})
        self.assertEqual(res.data['status'], 'PENDING')

        paid_session = {'status': 'PAID', 'transaction_id': 'tx-1', 'transaction_status': 'SUCCESS',
                        'transaction_reference': 'REF-1'}
        payment = {'status': 'SUCCESS', 'requested_amount': '5000.00', 'currency': 'XOF',
                   'debited_amount': '5200.00', 'reference': 'REF-1'}
        res = self._verify(paid_session, payment)
        self.assertEqual(res.data['status'], 'PAID')
        self.assertTrue(self.template.is_owned_by(self.user))
        self.assertEqual(TemplatePurchase.objects.get().amount_charged, Decimal('5200.00'))

    def test_underpaid_transaction_is_not_accepted(self):
        self.purchase()
        res = self._verify({'status': 'PAID', 'transaction_id': 'tx-1', 'transaction_status': 'SUCCESS'},
                           {'status': 'SUCCESS', 'requested_amount': '100.00', 'currency': 'XOF'})
        self.assertEqual(res.data['status'], 'PENDING')
        self.assertFalse(self.template.is_owned_by(self.user))

    def test_expired_session_is_cancelled(self):
        self.purchase()
        res = self._verify({'status': 'EXPIRED', 'transaction_id': None})
        self.assertEqual(res.data['status'], 'CANCELLED')

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

    def _webhook(self, body, secret='whsec_test', ts=None):
        raw = json.dumps(body).encode()
        ts = str(ts or int(time.time()))
        sig = hmac.new(secret.encode(), f'{ts}.'.encode() + raw, hashlib.sha256).hexdigest()
        return self.client.generic('POST', '/modeles/webhook/saspay/', raw, content_type='application/json',
                                   HTTP_X_WEBHOOK_SIGNATURE=sig, HTTP_X_WEBHOOK_TIMESTAMP=ts)

    def test_webhook_rejects_bad_signature_and_old_timestamp(self):
        event = {'event': 'transaction.success', 'data': {'id': 'tx-1'}}
        self.assertEqual(self._webhook(event, secret='wrong').status_code, 401)
        self.assertEqual(self._webhook(event, ts=int(time.time()) - 3600).status_code, 401)

    def test_webhook_confirms_purchase_through_api(self):
        self.purchase()
        responses = [
            fake_response(200, {'status': 'PAID', 'transaction_id': 'tx-9', 'transaction_status': 'SUCCESS'}),
            fake_response(200, {'status': 'SUCCESS', 'requested_amount': '5000.00', 'currency': 'XOF'}),
        ]
        with mock.patch('modeles.saspay.requests.request', side_effect=responses):
            res = self._webhook({'event': 'transaction.success', 'data': {'id': 'tx-9', 'status': 'SUCCESS'}})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(TemplatePurchase.objects.get().status, 'PAID')


class CoverRenderingTests(APITestCase):
    def test_every_style_renders_and_escapes(self):
        for template in MemoirTemplate.objects.all():
            data = cover_data(template)
            data['title'] = '<script>alert(1)</script>'
            html = render_cover_html(template, data)
            self.assertIn('&lt;script&gt;', html, template.slug)
            self.assertNotIn('<script>', html, template.slug)
