from django.test import override_settings
from rest_framework.test import APITestCase

from .models import User

PASSWORD = 'Motdepasse-Solide-2026'


def register_payload(role, **extra):
    data = {
        'email': f'{role.lower()}@test.com',
        'first_name': 'Awa',
        'last_name': 'Traoré',
        'password': PASSWORD,
        'password2': PASSWORD,
        'role': role,
        'language': 'fr',
    }
    data.update(extra)
    return data


class RegisterByRoleTests(APITestCase):
    url = '/users/register/'

    def test_student_registration(self):
        res = self.client.post(self.url, register_payload('STUDENT', university='USTTB', level='MASTER'))
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['user']['role'], 'STUDENT')
        self.assertIn('access', res.data)

    def test_student_requires_university_and_level(self):
        res = self.client.post(self.url, register_payload('STUDENT'))
        self.assertEqual(res.status_code, 400)
        self.assertIn('university', res.data)
        self.assertIn('level', res.data)

    def test_supervisor_and_co_supervisor_registration(self):
        for role in ('SUPERVISOR', 'CO_SUPERVISOR'):
            res = self.client.post(self.url, register_payload(role, university='USTTB', academic_title='Dr'))
            self.assertEqual(res.status_code, 201, res.data)
            self.assertEqual(res.data['user']['role'], role)

    def test_supervisor_requires_title(self):
        res = self.client.post(self.url, register_payload('SUPERVISOR', university='USTTB'))
        self.assertEqual(res.status_code, 400)
        self.assertIn('academic_title', res.data)

    def test_jury_registration(self):
        res = self.client.post(self.url, register_payload('JURY', academic_title='Pr'))
        self.assertEqual(res.status_code, 201, res.data)

    @override_settings(ADMIN_REGISTRATION_CODE='secret-code')
    def test_admin_registration_needs_valid_code(self):
        res = self.client.post(self.url, register_payload('ADMIN', admin_code='mauvais'))
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.filter(role='ADMIN').exists())

        res = self.client.post(self.url, register_payload('ADMIN', admin_code='secret-code'))
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(User.objects.get(role='ADMIN').is_staff)

    @override_settings(ADMIN_REGISTRATION_CODE='')
    def test_admin_registration_disabled_without_server_code(self):
        res = self.client.post(self.url, register_payload('ADMIN', admin_code=''))
        self.assertEqual(res.status_code, 400)


class LoginByRoleTests(APITestCase):
    def setUp(self):
        User.objects.create_user('enc@test.com', PASSWORD, first_name='A', last_name='B', role='SUPERVISOR')

    def test_login_with_matching_role(self):
        res = self.client.post('/users/login/', {'email': 'enc@test.com', 'password': PASSWORD, 'role': 'SUPERVISOR'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['user']['role'], 'SUPERVISOR')

    def test_login_in_wrong_space_is_refused(self):
        res = self.client.post('/users/login/', {'email': 'enc@test.com', 'password': PASSWORD, 'role': 'STUDENT'})
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data['role'], 'SUPERVISOR')

    def test_suspended_user_cannot_login(self):
        User.objects.filter(email='enc@test.com').update(is_active=False)
        res = self.client.post('/users/login/', {'email': 'enc@test.com', 'password': PASSWORD})
        self.assertEqual(res.status_code, 401)


class AdminEndpointsTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin@test.com', PASSWORD, first_name='A', last_name='D', role='ADMIN')
        self.student = User.objects.create_user('etu@test.com', PASSWORD, first_name='E', last_name='T')

    def test_non_admin_is_forbidden(self):
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get('/users/admin/users/').status_code, 403)
        self.assertEqual(self.client.get('/users/admin/stats/').status_code, 403)

    def test_admin_can_change_role_and_suspend(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(f'/users/admin/users/{self.student.id}/', {'role': 'JURY', 'is_active': False})
        self.assertEqual(res.status_code, 200, res.data)
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, 'JURY')
        self.assertFalse(self.student.is_active)

    def test_admin_cannot_demote_self(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(f'/users/admin/users/{self.admin.id}/', {'role': 'STUDENT'})
        self.assertEqual(res.status_code, 400)

    def test_stats(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get('/users/admin/stats/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['users_total'], 2)


class SecurityHardeningTests(APITestCase):
    """Protections contre la force brute, en-têtes de sécurité, surfaces d'attaque fermées."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = User.objects.create_user('cible@test.com', PASSWORD, first_name='C', last_name='B')

    def login(self, password, email='cible@test.com'):
        return self.client.post('/users/login/', {'email': email, 'password': password}, format='json')

    def test_account_locked_after_repeated_failures_even_with_right_password(self):
        from django.conf import settings
        for _ in range(settings.LOGIN_MAX_FAILURES):
            self.assertEqual(self.login('mauvais-mot-de-passe').status_code, 401)
        res = self.login(PASSWORD)
        self.assertEqual(res.status_code, 429)
        self.assertIn('Trop de tentatives', res.data['error'])

    def test_django_admin_login_is_locked_too(self):
        from django.conf import settings
        from django.contrib.auth import authenticate
        for _ in range(settings.LOGIN_MAX_FAILURES):
            self.assertIsNone(authenticate(email='cible@test.com', password='x'))
        self.assertIsNone(authenticate(email='cible@test.com', password=PASSWORD))

    def test_success_resets_failure_counter(self):
        for _ in range(3):
            self.login('mauvais')
        self.assertEqual(self.login(PASSWORD).status_code, 200)
        for _ in range(3):
            self.login('mauvais')
        self.assertEqual(self.login(PASSWORD).status_code, 200)

    def test_unknown_account_gets_same_answer(self):
        self.assertEqual(self.login('x', email='inconnu@test.com').data, self.login('x').data)

    def test_login_rate_limited_per_ip(self):
        from unittest import mock

        from rest_framework.throttling import ScopedRateThrottle
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'login': '3/min'}):
            codes = [self.login('x', email=f'u{i}@test.com').status_code for i in range(5)]
        self.assertEqual(codes, [401, 401, 401, 429, 429])

    def test_endpoints_closed_by_default(self):
        self.assertEqual(self.client.get('/projects/projects/').status_code, 401)
        self.assertEqual(self.client.get('/projects/trash/').status_code, 401)
        # Documentation : absente en production (404), réservée aux administrateurs sinon (401).
        self.assertIn(self.client.get('/swagger/').status_code, (401, 404))

    @override_settings(GOOGLE_CLIENT_ID='')
    def test_google_login_disabled_without_client_id(self):
        res = self.client.post('/users/google/', {'id_token': 'jeton'}, format='json')
        self.assertEqual(res.status_code, 404)

    @override_settings(GOOGLE_CLIENT_ID='mon-app.apps.googleusercontent.com')
    def test_google_token_for_another_app_rejected(self):
        from unittest import mock
        answer = mock.Mock(status_code=200)
        answer.json.return_value = {'aud': 'autre-app.apps.googleusercontent.com', 'iss': 'accounts.google.com',
                                    'email': 'cible@test.com', 'email_verified': 'true'}
        with mock.patch('users.views.requests.get', return_value=answer):
            res = self.client.post('/users/google/', {'id_token': 'jeton'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertNotIn('access', res.data)

    def test_security_headers(self):
        res = self.client.get('/users/profile/')
        self.assertIn("default-src 'none'", res['Content-Security-Policy'])
        self.assertIn("frame-ancestors 'none'", res['Content-Security-Policy'])
        self.assertEqual(res['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(res['X-Frame-Options'], 'DENY')
        self.assertIn('camera=()', res['Permissions-Policy'])

    def test_password_change_revokes_other_sessions(self):
        other_device = self.login(PASSWORD).data['refresh']
        self.client.force_authenticate(self.user)
        res = self.client.post('/users/change-password/', {'old_password': PASSWORD,
                                                            'new_password': 'Nouveau-Mot-De-Passe-2026'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/users/refresh/', {'refresh': other_device}, format='json').status_code, 401)
        self.assertEqual(self.client.post('/users/refresh/', {'refresh': res.data['refresh']}, format='json').status_code, 200)


class PasswordResetTests(APITestCase):
    """Mot de passe oublié : lien envoyé par email, valable une seule fois."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = User.objects.create_user('oubli@test.com', PASSWORD, first_name='Awa', last_name='T',
                                             role='SUPERVISOR', university='U', academic_title='Dr')

    def request_reset(self, email='oubli@test.com'):
        return self.client.post('/users/password-reset/', {'email': email}, format='json')

    def link_params(self):
        import re
        from urllib.parse import parse_qs, urlparse

        from django.core import mail
        body = mail.outbox[-1].body
        url = re.search(r'https?://\S+/reinitialiser-mot-de-passe\?\S+', body).group(0)
        query = parse_qs(urlparse(url).query)
        return {k: v[0] for k, v in query.items()}

    def test_email_sent_to_account_address_with_link(self):
        from django.core import mail
        res = self.request_reset('OUBLI@test.com')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['oubli@test.com'])
        self.assertIn('Réinitialisation', mail.outbox[0].subject)
        params = self.link_params()
        self.assertEqual(params['espace'], 'encadreur')  # retour vers l'espace de connexion du compte
        self.assertTrue(params['uid'] and params['token'])

    def test_unknown_email_gets_same_answer_and_no_mail(self):
        from django.core import mail
        known = self.request_reset().data
        unknown = self.request_reset('personne@test.com').data
        self.assertEqual(known, unknown)
        self.assertEqual(len(mail.outbox), 1)

    def test_reset_changes_password_once_and_logs_out_everywhere(self):
        old_refresh = self.client.post('/users/login/', {'email': 'oubli@test.com', 'password': PASSWORD},
                                       format='json').data['refresh']
        self.request_reset()
        params = self.link_params()
        new = 'Tout-Nouveau-Secret-2026'
        res = self.client.post('/users/password-reset/confirm/',
                               {'uid': params['uid'], 'token': params['token'], 'new_password': new}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.client.post('/users/login/', {'email': 'oubli@test.com', 'password': new},
                                          format='json').status_code, 200)
        self.assertEqual(self.client.post('/users/refresh/', {'refresh': old_refresh}, format='json').status_code, 401)
        # Le lien ne sert qu'une fois.
        again = self.client.post('/users/password-reset/confirm/',
                                 {'uid': params['uid'], 'token': params['token'], 'new_password': 'Autre-Secret-2026'},
                                 format='json')
        self.assertEqual(again.status_code, 400)

    def test_invalid_token_and_weak_password_rejected(self):
        self.request_reset()
        params = self.link_params()
        res = self.client.post('/users/password-reset/confirm/',
                               {'uid': params['uid'], 'token': 'faux-jeton', 'new_password': 'Tout-Nouveau-2026'},
                               format='json')
        self.assertEqual(res.status_code, 400)
        res = self.client.post('/users/password-reset/confirm/',
                               {'uid': params['uid'], 'token': params['token'], 'new_password': '1234'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertTrue(self.user.__class__.objects.get(pk=self.user.pk).check_password(PASSWORD))

    def test_reset_unlocks_locked_account(self):
        from django.conf import settings
        for _ in range(settings.LOGIN_MAX_FAILURES):
            self.client.post('/users/login/', {'email': 'oubli@test.com', 'password': 'x'}, format='json')
        self.request_reset()
        params = self.link_params()
        new = 'Tout-Nouveau-Secret-2026'
        self.client.post('/users/password-reset/confirm/',
                         {'uid': params['uid'], 'token': params['token'], 'new_password': new}, format='json')
        self.assertEqual(self.client.post('/users/login/', {'email': 'oubli@test.com', 'password': new},
                                          format='json').status_code, 200)

    @override_settings(TESTING=False, DEBUG=False, EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_clear_error_when_email_not_configured(self):
        res = self.request_reset()
        self.assertEqual(res.status_code, 503)
        self.assertIn('pas encore configuré', res.data['error'])
