from rest_framework.test import APITestCase

from users.models import User
from .models import Project, Chapter

PASSWORD = 'Motdepasse-Solide-2026'


def make_user(email, role):
    return User.objects.create_user(email, PASSWORD, first_name='X', last_name='Y', role=role)


class SupervisionWorkflowTests(APITestCase):
    def setUp(self):
        self.student = make_user('etu@test.com', 'STUDENT')
        self.other_student = make_user('etu2@test.com', 'STUDENT')
        self.supervisor = make_user('enc@test.com', 'SUPERVISOR')
        self.jury = make_user('jury@test.com', 'JURY')
        self.project = Project.objects.create(user=self.student, title='Mémoire', supervisor=self.supervisor)
        self.project.jury.add(self.jury)
        Chapter.objects.create(project=self.project, title='Introduction', content='...')

    def url(self, suffix=''):
        return f'/projects/projects/{self.project.id}/{suffix}'

    def test_visibility_per_role(self):
        for user, expected in (
            (self.student, 1), (self.supervisor, 1), (self.jury, 1), (self.other_student, 0),
        ):
            self.client.force_authenticate(user)
            res = self.client.get('/projects/projects/')
            self.assertEqual(len(res.data), expected, user.email)

    def test_supervisor_reads_chapters_but_cannot_edit(self):
        self.client.force_authenticate(self.supervisor)
        chapters = self.client.get(f'/projects/chapters/?project={self.project.id}').data
        self.assertEqual(len(chapters), 1)
        res = self.client.patch(f'/projects/chapters/{chapters[0]["id"]}/', {'content': 'piraté'})
        self.assertEqual(res.status_code, 403)
        res = self.client.patch(self.url(), {'title': 'piraté'})
        self.assertEqual(res.status_code, 403)

    def test_assigning_wrong_role_as_supervisor_is_rejected(self):
        self.client.force_authenticate(self.student)
        res = self.client.patch(self.url(), {'supervisor': self.jury.id})
        self.assertEqual(res.status_code, 400)

    def test_submit_then_request_changes_then_approve(self):
        self.client.force_authenticate(self.student)
        res = self.client.post(self.url('submit_review/'))
        self.assertEqual(res.data['status'], 'REVIEW')

        self.client.force_authenticate(self.supervisor)
        res = self.client.post(self.url('review/'), {'decision': 'request_changes', 'comment': 'Revoir la problématique'})
        self.assertEqual(res.data['status'], 'IN_PROGRESS')

        self.client.force_authenticate(self.student)
        self.client.post(self.url('submit_review/'))

        self.client.force_authenticate(self.supervisor)
        res = self.client.post(self.url('review/'), {'decision': 'approve'})
        self.assertEqual(res.data['status'], 'VALIDATED')

    def test_outsider_cannot_review(self):
        self.client.force_authenticate(self.student)
        self.client.post(self.url('submit_review/'))
        outsider = make_user('enc2@test.com', 'SUPERVISOR')
        self.client.force_authenticate(outsider)
        res = self.client.post(self.url('review/'), {'decision': 'approve'})
        self.assertEqual(res.status_code, 404)

    def test_archive_and_restore(self):
        self.client.force_authenticate(self.student)
        self.client.post(self.url('submit_review/'))
        res = self.client.post(self.url('archive/'))
        self.assertEqual(res.data['status'], 'ARCHIVED')
        res = self.client.post(self.url('restore/'))
        self.assertEqual(res.data['status'], 'REVIEW')
