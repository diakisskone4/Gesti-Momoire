"""Tests de l'API de paiement mobile money (Orange Money, Moov Money, Wave)."""
import time
from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from notifications.models import Notification
from . import mobile_money as mm
from .models import MemoirTemplate, PaymentDevice, PaymentMessage, TemplatePurchase
from .tests import make_user

NUMBER = '+223 70 00 00 01'
REF = 'PP261124.1530.A12345'
SMS = (f'Vous avez recu un transfert de 5000.00 FCFA du 76123456. Frais 0 FCFA. '
       f'ID transaction: {REF}. Nouveau solde: 98000.00 FCFA.')


@override_settings(PAYMENT_NUMBER=NUMBER, PAYMENT_NUMBERS={'moov': '+22360000002'})
class ReadingTests(SimpleTestCase):
    def test_amounts(self):
        for text, expected in [
            ('Vous avez reçu 5 000 FCFA de Awa', '5000'), ('Recu: 5.000F de Awa', '5000'),
            ('Montant 5,000 XOF recu', '5000'), ('Vous avez recu 5000.00 FCFA', '5000.00'),
            ('recu FCFA 5000 de 76123456', '5000'), ('recu 1 250 000,50 F CFA', '1250000.50'),
            ('Solde: 98 000 FCFA. Vous avez recu 100 FCFA', '100'),  # le solde n'est jamais le montant
            ('Vous avez recu 100F. Nouveau solde 5000F', '100'),
            ('recu du 76123456 5000 FCFA', None),  # ambigu : vérification manuelle
            ('Bonjour', None),
        ]:
            self.assertEqual(mm.read_amount(text), Decimal(expected) if expected else None, text)

    def test_only_incoming_transfers(self):
        self.assertTrue(mm.is_incoming(SMS))
        self.assertTrue(mm.is_incoming('Votre compte a été crédité de 5000F'))
        for text in ('Vous avez envoyé 5000F à 76123456', 'Transfert échoué. Montant reçu : 0',
                     'Votre transfert de 5000F a été reçu par 76123456', 'Votre code de retrait est 123456'):
            self.assertFalse(mm.is_incoming(text), text)

    def test_references_exclude_phones_amounts_dates(self):
        text = SMS + ' Le 24/11/2026 à 15:30:12 +22376123456 5000FCFA T_ABC12345. Tx 123456789012'
        refs = mm.read_references(text)
        self.assertIn('PP2611241530A12345', refs)
        self.assertIn('TABC12345', refs)
        self.assertIn('123456789012', refs)
        for bad in ('76123456', '22376123456', '500000', '9800000', '24112026', '153012', '5000FCFA'):
            self.assertNotIn(bad, refs)

    def test_phones(self):
        self.assertEqual(mm.read_phones('de +223 76 12 34 56 vers 70000001 ou 60 00 00 02 le 24/11/2026'), {'76123456'})
        self.assertEqual(mm.clean_phone('00223 76.12.34.56'), '76123456')
        self.assertEqual(mm.clean_phone('1234'), '')


@override_settings(PAYMENT_NUMBER=NUMBER, PAYMENT_NUMBERS={'moov': '+22360000002'}, PAYMENT_HOLDER='Titulaire', PAYMENT_NOTIFY_EMAILS=[])
class MobileMoneyTests(APITestCase):
    def setUp(self):
        self.user = make_user('etu@test.com')
        self.admin = make_user('admin@test.com', role='ADMIN')
        self.template = MemoirTemplate.objects.get(slug='master-agronomie-environnement')
        self.other = MemoirTemplate.objects.filter(price__gt=0).exclude(pk=self.template.pk).first()
        self.client.force_authenticate(self.user)
        self.staff = APIClient()
        self.staff.force_authenticate(self.admin)
        self.phone = APIClient()
        _, self.token = mm.pair_device('Téléphone')

    def buy(self, client=None, template=None):
        return (client or self.client).post(f'/modeles/{(template or self.template).slug}/purchase/').data['id']

    def declare(self, pk, client=None, **data):
        return (client or self.client).post(f'/modeles/achats/{pk}/declare/', {
            'operator': 'orange', 'phone': '76 12 34 56', 'reference': REF, **data})

    def send(self, text=SMS, operator='orange', when=None, token=None):
        return self.phone.post('/modeles/paiement/messages/', {'messages': [
            {'operator': operator, 'text': text, 'received_at': int((when or time.time()) * 1000)}]},
            format='json', HTTP_X_DEVICE_TOKEN=self.token if token is None else token)

    def test_options(self):
        data = self.client.get('/modeles/paiement/').data
        self.assertEqual(data['mode'], 'mobile_money')
        # Chaque opérateur a son numéro ; à défaut, le numéro général.
        self.assertEqual([(o['code'], o['number'], o['number_display']) for o in data['operators']],
                         [('orange', '70000001', '70 00 00 01'), ('moov', '60000002', '60 00 00 02'),
                          ('wave', '70000001', '70 00 00 01')])
        with override_settings(PAYMENT_NUMBER=''):
            self.assertEqual(self.client.get('/modeles/paiement/').data, {'mode': 'jemeni'})

    def test_purchase_is_reused_and_never_paid_by_declaration_alone(self):
        pk = self.buy()
        self.assertEqual(self.buy(), pk)
        res = self.declare(pk)
        self.assertEqual((res.status_code, res.data['status']), (200, 'SUBMITTED'))
        self.assertEqual(self.client.post(f'/modeles/achats/{pk}/verify/').data['status'], 'SUBMITTED')
        self.assertEqual(self.buy(), pk)
        self.assertFalse(self.template.is_owned_by(self.user))
        # Administrateur prévenu une seule fois, même si le client corrige sa référence.
        self.declare(pk, reference='PP999999.0001')
        self.assertEqual(Notification.objects.filter(recipient=self.admin).count(), 1)
        self.assertEqual([m.to for m in mail.outbox], [['admin@test.com']])

    def test_invalid_declarations(self):
        pk = self.buy()
        for data in ({'operator': 'paypal'}, {'phone': '123'}, {'phone': NUMBER}, {'phone': '60 00 00 02'}, {'reference': 'abc'},
                     {'reference': '76123456'}, {'reference': '+22376123456'}, {'reference': ''}):
            self.assertEqual(self.declare(pk, **data).status_code, 400, data)
        stranger = APIClient()
        stranger.force_authenticate(make_user('autre@test.com'))
        self.assertEqual(self.declare(pk, client=stranger).status_code, 404)

    def test_message_after_declaration_confirms(self):
        pk = self.buy()
        self.declare(pk)
        self.assertEqual(self.send().data['kept'], 1)
        purchase = TemplatePurchase.objects.get(pk=pk)
        self.assertEqual((purchase.status, purchase.amount_charged), ('PAID', Decimal('5000')))
        self.assertTrue(self.template.is_owned_by(self.user))
        self.assertTrue(Notification.objects.filter(recipient=self.user, verb__startswith='Achat confirmé').exists())

    def test_message_before_declaration_confirms(self):
        pk = self.buy()
        self.send()
        self.assertEqual(self.declare(pk).data['status'], 'PAID')
        self.assertEqual(len(mail.outbox), 0)  # rien à vérifier

    def test_same_message_is_stored_once(self):
        now = time.time()
        self.send(when=now)
        self.send(when=now)
        self.assertEqual(PaymentMessage.objects.count(), 1)

    def test_doubtful_messages_never_confirm(self):
        pk = self.buy()
        self.declare(pk)
        cases = [
            dict(text=SMS.replace('5000.00', '4999.00')),             # montant insuffisant
            dict(text=SMS.replace('5000.00', '100').replace('98000.00', '5000.00')),  # 5000 = le solde
            dict(text=SMS.replace('76123456', '77999999')),           # payé par un autre numéro
            dict(text=SMS.replace(REF, 'PP000000.0000.Z99999')),      # autre transaction
            dict(operator='moov'),                                    # autre opérateur
            dict(when=time.time() - 3600),                            # reçu avant l'achat
            dict(text=f'Vous avez envoye 5000 FCFA au 76123456. ID: {REF}'),
        ]
        for case in cases:
            self.assertEqual(self.send(**case).status_code, 200)
            self.assertEqual(TemplatePurchase.objects.get(pk=pk).status, 'SUBMITTED', case)
        self.assertEqual(self.client.post(f'/modeles/achats/{pk}/verify/').data['status'], 'SUBMITTED')

    def test_one_transaction_pays_one_purchase(self):
        first, second = self.buy(), self.buy(template=self.other)
        self.declare(second)
        self.declare(first)
        self.send()
        self.assertEqual(TemplatePurchase.objects.filter(status='PAID').count(), 1)
        left = TemplatePurchase.objects.get(status='SUBMITTED')
        self.assertEqual(self.staff.post(f'/modeles/admin/paiements/{left.pk}/approve/').status_code, 400)
        left.refresh_from_db()
        self.assertEqual(left.status, 'SUBMITTED')
        thief = APIClient()
        thief.force_authenticate(make_user('voleur@test.com'))
        self.assertEqual(self.declare(self.buy(client=thief), client=thief).status_code, 400)

    def test_device_token_required_and_revocable(self):
        for token in ('', 'faux'):
            self.assertEqual(self.send(token=token).status_code, 401)
        self.assertFalse(PaymentMessage.objects.exists())
        device = PaymentDevice.objects.get()
        self.assertNotEqual(device.token_hash, self.token)
        self.assertIsNone(device.last_seen_at)
        self.send(text='Votre code secret est 1234')  # message sans rapport : jamais conservé
        self.assertFalse(PaymentMessage.objects.exists())
        device.refresh_from_db()
        self.assertIsNotNone(device.last_seen_at)
        self.staff.delete(f'/modeles/admin/telephones/{device.pk}/')
        self.assertEqual(self.send().status_code, 401)

    def test_bad_device_payloads(self):
        def post(payload):
            return self.phone.post('/modeles/paiement/messages/', payload, format='json',
                                   HTTP_X_DEVICE_TOKEN=self.token).status_code
        for payload in ({}, {'messages': 'x'}, {'messages': [{}] * 21}, []):
            self.assertEqual(post(payload), 400, payload)
        for item in (None, {'text': 1}, {'text': SMS, 'operator': None},
                     {'text': SMS, 'operator': 'orange', 'received_at': 'x'},
                     {'text': SMS + '\x00', 'operator': 'orange', 'received_at': 10 ** 30},
                     {'text': 'recu ' + '9' * 40 + ' FCFA', 'operator': 'orange', 'received_at': -1}):
            self.assertEqual(post({'messages': [item]}), 200, item)

    def test_admin_routes_are_admin_only(self):
        pk = self.buy()
        self.declare(pk)
        for method, path in (('get', 'paiements/'), ('get', 'paiements/messages/'),
                             ('post', f'paiements/{pk}/approve/'), ('post', f'paiements/{pk}/reject/'),
                             ('get', 'telephones/'), ('post', 'telephones/')):
            self.assertEqual(getattr(self.client, method)(f'/modeles/admin/{path}').status_code, 403, path)
            self.assertEqual(getattr(APIClient(), method)(f'/modeles/admin/{path}').status_code, 401, path)
        self.assertEqual(TemplatePurchase.objects.get(pk=pk).status, 'SUBMITTED')

    def test_admin_approves_with_suggested_message(self):
        pk = self.buy()
        self.declare(pk, reference='ERREUR12345')  # référence mal recopiée : le numéro concorde
        self.send()
        listed = self.staff.get('/modeles/admin/paiements/').data
        self.assertEqual([p['id'] for p in listed], [pk])
        self.assertEqual((listed[0]['buyer_email'], listed[0]['buyer_name']), ('etu@test.com', 'Awa Diallo'))
        message = listed[0]['suggestions'][0]['id']
        res = self.staff.post(f'/modeles/admin/paiements/{pk}/approve/', {'message_id': message})
        self.assertEqual((res.status_code, res.data['status'], res.data['automatic']), (200, 'PAID', False))
        self.assertEqual(TemplatePurchase.objects.get(pk=pk).reviewed_by, self.admin)
        self.assertEqual(self.staff.get('/modeles/admin/paiements/').data, [])
        self.assertEqual(len(self.staff.get('/modeles/admin/paiements/?etat=tous').data), 1)

    def test_admin_rejects_then_client_can_buy_again(self):
        pk = self.buy()
        self.assertEqual(self.staff.post(f'/modeles/admin/paiements/{pk}/approve/').status_code, 404)  # rien déclaré
        self.declare(pk)
        self.assertEqual(self.staff.post(f'/modeles/admin/paiements/{pk}/reject/', {}).status_code, 400)
        res = self.staff.post(f'/modeles/admin/paiements/{pk}/reject/', {'reason': 'Aucun transfert reçu.'})
        self.assertEqual((res.data['status'], res.data['review_note']), ('FAILED', 'Aucun transfert reçu.'))
        self.assertFalse(self.template.is_owned_by(self.user))
        self.assertEqual(self.declare(pk).status_code, 400)
        self.assertNotEqual(self.buy(), pk)

    def test_pairing_token_is_shown_once(self):
        res = self.staff.post('/modeles/admin/telephones/', {'name': 'Samsung'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.send(token=res.data['token']).status_code, 200)
        self.assertNotIn('token', self.staff.get('/modeles/admin/telephones/').data[0])

    def test_old_unmatched_messages_are_purged(self):
        self.send()
        PaymentMessage.objects.update(received_at=timezone.now() - timedelta(days=100))
        self.send(text=SMS.replace(REF, 'PP111111.2222'))
        self.assertEqual(PaymentMessage.objects.count(), 1)
