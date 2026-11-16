"""Tests des correctifs d'accès, d'export, de notifications et de configuration."""
from rest_framework.test import APITestCase

from collaborations.models import Comment
from notifications.models import Notification
from users.models import User
from .models import Chapter, Project, Reference

PASSWORD = 'Motdepasse-Solide-2026'


def make_user(email, role='STUDENT'):
    return User.objects.create_user(email, PASSWORD, first_name='X', last_name='Y', role=role)


class AccessControlTests(APITestCase):
    def setUp(self):
        self.student = make_user('etu@test.com')
        self.intruder = make_user('intrus@test.com')
        self.supervisor = make_user('enc@test.com', 'SUPERVISOR')
        self.project = Project.objects.create(user=self.student, title='Mémoire secret', supervisor=self.supervisor)
        self.chapter = Chapter.objects.create(project=self.project, title='Intro', content='Texte')
        self.ref = Reference.objects.create(project=self.project, title='Livre', authors='Diallo, A.', year=2020)

    def test_project_files_are_not_served(self):
        self.assertEqual(self.client.get('/.env').status_code, 404)
        self.assertEqual(self.client.get('/manage.py').status_code, 404)

    def test_intruder_cannot_read_references(self):
        self.client.force_authenticate(self.intruder)
        res = self.client.get(f'/projects/references/?project_id={self.project.id}')
        self.assertEqual(res.data, [])
        self.assertEqual(self.client.get(f'/projects/references/{self.ref.id}/').status_code, 404)

    def test_intruder_cannot_add_reference(self):
        self.client.force_authenticate(self.intruder)
        res = self.client.post('/projects/references/', {
            'project': self.project.id, 'title': 'x', 'authors': 'y', 'year': 2020,
        })
        self.assertEqual(res.status_code, 403)

    def test_supervisor_reads_but_cannot_edit_references(self):
        self.client.force_authenticate(self.supervisor)
        self.assertEqual(len(self.client.get(f'/projects/references/?project_id={self.project.id}').data), 1)
        self.assertEqual(self.client.delete(f'/projects/references/{self.ref.id}/').status_code, 403)

    def test_bibtex(self):
        self.client.force_authenticate(self.student)
        res = self.client.get(f'/projects/references/{self.ref.id}/bibtex/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('@article{diallo2020', res.data['bibtex'])

    def test_comments_are_private_and_notify(self):
        self.client.force_authenticate(self.supervisor)
        res = self.client.post('/projects/comments/', {'project': self.project.id, 'content': 'Revoir intro'})
        self.assertEqual(res.status_code, 201)
        self.assertTrue(Notification.objects.filter(recipient=self.student, verb='a commenté').exists())

        self.client.force_authenticate(self.intruder)
        self.assertEqual(self.client.get(f'/projects/comments/?project_id={self.project.id}').data, [])
        res = self.client.post('/projects/comments/', {'project': self.project.id, 'content': 'spam'})
        self.assertEqual(res.status_code, 403)

    def test_chapter_comment_without_project_is_attached(self):
        self.client.force_authenticate(self.student)
        res = self.client.post('/projects/comments/', {'chapter': self.chapter.id, 'content': 'note'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Comment.objects.get().project_id, self.project.id)

    def test_validation_requires_reviewer_of_project(self):
        other_sup = make_user('enc2@test.com', 'SUPERVISOR')
        self.client.force_authenticate(other_sup)
        res = self.client.post('/projects/validations/', {'project': self.project.id, 'status': 'APPROVED'})
        self.assertEqual(res.status_code, 403)
        self.client.force_authenticate(self.supervisor)
        res = self.client.post('/projects/validations/', {'project': self.project.id, 'status': 'APPROVED'})
        self.assertEqual(res.status_code, 201)

    def test_search_is_limited_to_visible_projects(self):
        self.client.force_authenticate(self.intruder)
        self.assertEqual(self.client.get('/documents/search/?q=secret').data['results'], [])
        self.client.force_authenticate(self.student)
        self.assertEqual(len(self.client.get('/documents/search/?q=secret').data['results']), 1)

    def test_only_owner_can_generate_plan_or_reorder(self):
        self.client.force_authenticate(self.supervisor)
        self.assertEqual(self.client.post(f'/projects/projects/{self.project.id}/generate_plan/').status_code, 403)
        self.assertEqual(self.client.post(f'/projects/chapters/{self.chapter.id}/reorder/', {'order': 3}).status_code, 403)

    def test_collaborators(self):
        friend = make_user('ami@test.com')
        self.client.force_authenticate(self.student)
        res = self.client.post('/projects/collaborators/', {'project': self.project.id, 'email': 'ami@test.com', 'role': 'editor'})
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data['can_edit'])
        self.client.force_authenticate(self.intruder)
        res = self.client.post('/projects/collaborators/', {'project': self.project.id, 'email': friend.email})
        self.assertEqual(res.status_code, 404)

    def test_share_links(self):
        self.client.force_authenticate(self.student)
        res = self.client.post('/projects/share-links/', {'project': self.project.id}, format='json')
        self.assertEqual(res.status_code, 201)
        token = res.data['token']
        self.assertEqual(len(self.client.get(f'/projects/share-links/?project={self.project.id}').data), 1)
        self.assertEqual(self.client.delete(f'/projects/share-links/{token}/').status_code, 204)


class ExportTests(APITestCase):
    def setUp(self):
        self.student = make_user('etu@test.com')
        self.project = Project.objects.create(user=self.student, title='Mémoire <test>', theme='IA')
        intro = Chapter.objects.create(project=self.project, title='Introduction', content='Ligne 1\nLigne 2' * 200)
        Chapter.objects.create(project=self.project, parent=intro, title='Contexte', content='Détails')
        Reference.objects.create(project=self.project, title='Livre', authors='Diallo, A.', year=2020)
        self.client.force_authenticate(self.student)

    def export(self, fmt):
        return self.client.post(f'/projects/projects/{self.project.id}/export/', {'format': fmt}, format='json')

    def test_html_is_real_html_and_escaped(self):
        res = self.export('html')
        self.assertEqual(res.status_code, 200)
        body = res.content.decode()
        self.assertTrue(body.startswith('<!DOCTYPE html>'))
        self.assertIn('Mémoire &lt;test&gt;', body)
        self.assertIn('Contexte', body)
        self.assertIn('Bibliographie', body)

    def test_pdf_and_docx(self):
        for fmt, magic in (('pdf', b'%PDF'), ('docx', b'PK')):
            res = self.export(fmt)
            self.assertEqual(res.status_code, 200, fmt)
            self.assertTrue(b''.join(res.streaming_content).startswith(magic), fmt)

    def test_unknown_format(self):
        self.assertEqual(self.export('exe').status_code, 400)


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user = make_user('etu@test.com')
        self.other = make_user('autre@test.com')
        project = Project.objects.create(user=self.user, title='M')
        for i in range(3):
            Notification.objects.create(recipient=self.user, verb='a commenté', target_type='project', target_id=project.id)
        self.foreign = Notification.objects.create(recipient=self.other, verb='x', target_type='project', target_id=project.id)
        self.client.force_authenticate(self.user)

    def test_list_count_and_mark_read(self):
        self.assertEqual(len(self.client.get('/notifications/').data), 3)
        self.assertEqual(self.client.get('/notifications/unread_count/').data['count'], 3)
        first = Notification.objects.filter(recipient=self.user).first()
        self.assertTrue(self.client.post(f'/notifications/{first.id}/mark_read/').data['read'])
        self.assertEqual(self.client.post('/notifications/mark_all_read/').data['updated'], 2)
        self.assertEqual(self.client.get('/notifications/unread_count/').data['count'], 0)

    def test_cannot_touch_other_users_notifications(self):
        self.assertEqual(self.client.post(f'/notifications/{self.foreign.id}/mark_read/').status_code, 404)


class PasswordTests(APITestCase):
    def test_weak_new_password_is_refused(self):
        user = make_user('etu@test.com')
        self.client.force_authenticate(user)
        res = self.client.post('/users/change-password/', {'old_password': PASSWORD, 'new_password': '123'})
        self.assertEqual(res.status_code, 400)
        res = self.client.post('/users/change-password/', {'old_password': PASSWORD, 'new_password': 'Nouveau-Solide-2027'})
        self.assertEqual(res.status_code, 200)


class SharedLinkPublicTests(APITestCase):
    def test_public_read_and_revocation(self):
        student = make_user('etu@test.com')
        project = Project.objects.create(user=student, title='Partagé')
        Chapter.objects.create(project=project, title='Intro', content='Bonjour')
        self.client.force_authenticate(student)
        token = self.client.post('/projects/share-links/', {'project': project.id}, format='json').data['token']
        self.client.force_authenticate(None)
        res = self.client.get(f'/projects/shared/{token}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['chapters'][0]['content'], 'Bonjour')
        self.assertEqual(self.client.get('/projects/shared/inconnu/').status_code, 404)
