import json
from django.test import TestCase, RequestFactory
from .models import DashboardMessage
from .views import active_messages


class DashboardMessageModelTest(TestCase):
    def test_dashboard_message_str(self):
        message = DashboardMessage.objects.create(
            title='Welcome',
            content='Bienvenue sur le tableau de bord.',
            is_active=True,
        )
        self.assertEqual(str(message), 'Welcome')


class AdminDashboardViewsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_active_messages_returns_only_active(self):
        DashboardMessage.objects.create(title='Visible', content='Actif', is_active=True)
        DashboardMessage.objects.create(title='Hidden', content='Inactif', is_active=False)

        request = self.factory.get('/admin-dashboard/active-messages/')
        response = active_messages(request)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertIn('messages', data)
        self.assertEqual(len(data['messages']), 1)
        self.assertEqual(data['messages'][0]['title'], 'Visible')
