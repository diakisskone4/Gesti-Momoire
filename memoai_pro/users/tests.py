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
