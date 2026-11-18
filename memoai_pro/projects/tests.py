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


class AcademicExportFormatTests(APITestCase):
    """Export Word / PDF aux normes : Times New Roman 12, interligne 1,5, justifié, marges 4/2,5 cm,
    titres 16/14/13 pt gras, pagination, chaque partie sur une nouvelle page."""

    def setUp(self):
        self.user = make_user('export@test.com', 'STUDENT')
        self.client.force_authenticate(self.user)
        self.project = Project.objects.create(user=self.user, title='Mobile money au Mali', theme='Inclusion',
                                              desired_pages=40)
        parts = [('Dédicace', 'preliminary', 'À mes parents.'),
                 ('Remerciements', 'preliminary', '[Conseil du modèle : remerciez votre encadreur]\n\nMerci à tous.'),
                 ('Introduction générale', 'chapter', 'Le mobile money se développe rapidement. ' * 20)]
        for order, (title, kind, content) in enumerate(parts, start=1):
            Chapter.objects.create(project=self.project, title=title, type=kind, content=content, order=order)
        chapter = Chapter.objects.create(project=self.project, title='Chapitre 1 : Revue de la littérature',
                                         type='chapter', content='Ce chapitre présente les travaux.', order=4)
        section = Chapter.objects.create(project=self.project, parent=chapter, title='Définition des concepts',
                                         type='section', content='Le mobile money désigne...\n• Premier point', order=1)
        Chapter.objects.create(project=self.project, parent=section, title='Inclusion financière', type='section',
                               content='Sous-section détaillée.', order=1)

    def export(self, fmt):
        res = self.client.post(f'/projects/projects/{self.project.id}/export/', {'format': fmt}, format='json')
        self.assertEqual(res.status_code, 200)
        return b''.join(res.streaming_content) if hasattr(res, 'streaming_content') else res.content

    def test_word_follows_academic_rules(self):
        from io import BytesIO

        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Cm, Pt
        doc = Document(BytesIO(self.export('docx')))

        section = doc.sections[0]
        self.assertEqual((round(section.left_margin.cm, 2), round(section.right_margin.cm, 2),
                          round(section.top_margin.cm, 2), round(section.bottom_margin.cm, 2)), (4.0, 2.5, 2.5, 2.5))
        self.assertTrue(section.different_first_page_header_footer)  # pas de numéro sur la page de garde
        self.assertIn('PAGE', section.footer._element.xml)

        normal = doc.styles['Normal']
        self.assertEqual((normal.font.name, normal.font.size), ('Times New Roman', Pt(12)))
        self.assertEqual(str(normal.font.color.rgb), '000000')
        fmt = normal.paragraph_format
        self.assertEqual(fmt.line_spacing, 1.5)
        self.assertEqual(fmt.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)
        self.assertEqual((fmt.space_before, fmt.space_after), (Pt(6), Pt(6)))
        self.assertEqual(round(fmt.first_line_indent.cm, 2), 1.25)

        for level, size in ((1, 16), (2, 14), (3, 13)):
            style = doc.styles[f'Heading {level}']
            self.assertEqual((style.font.name, style.font.size, style.font.bold), ('Times New Roman', Pt(size), True))
            self.assertEqual(str(style.font.color.rgb), '000000')
        self.assertTrue(doc.styles['Heading 1'].font.all_caps)
        self.assertTrue(doc.styles['Heading 1'].paragraph_format.page_break_before)  # chaque partie sur une page

        headings = [(p.style.name, p.text) for p in doc.paragraphs if p.style.name.startswith('Heading')]
        self.assertEqual(headings, [
            ('Heading 1', 'Dédicace'), ('Heading 1', 'Remerciements'), ('Heading 1', 'Introduction générale'),
            ('Heading 1', 'Chapitre 1 : Revue de la littérature'), ('Heading 2', 'Définition des concepts'),
            ('Heading 3', 'Inclusion financière'),
        ])
        text = '\n'.join(p.text for p in doc.paragraphs)
        self.assertNotIn('Conseil du modèle', text)  # conseils de rédaction retirés du document final
        self.assertIn('Merci à tous.', text)

    def test_pdf_one_part_per_page_with_numbers(self):
        from io import BytesIO

        from PyPDF2 import PdfReader
        reader = PdfReader(BytesIO(self.export("pdf")))
        pages = [p.extract_text() for p in reader.pages]
        # Page de titre + Dédicace + Remerciements + Introduction + Chapitre 1 (avec ses sections)
        self.assertEqual(len(pages), 5)
        for page, title in zip(pages[1:], ('DÉDICACE', 'REMERCIEMENTS', 'INTRODUCTION GÉNÉRALE', 'CHAPITRE 1')):
            self.assertIn(title, page)
        self.assertIn('Définition des concepts', pages[4])
        self.assertNotIn('Conseil du modèle', ''.join(pages))
        # Numéro de page sur les pages 2 à 5 (dessiné avant le texte, donc extrait en premier), rien sur la page de titre.
        for number, page in enumerate(pages[1:], start=2):
            self.assertEqual(page.strip().splitlines()[0].strip(), str(number))
        self.assertTrue(pages[0].startswith('MOBILE MONEY AU MALI'))
        fonts = set()
        for page in reader.pages:
            for font in page['/Resources']['/Font'].values():
                fonts.add(str(font.get_object()['/BaseFont']))
        # Helvetica n'est que la police déclarée par défaut par reportlab : aucun texte ne l'utilise.
        self.assertTrue(fonts - {'/Helvetica'} <= {'/Times-Roman', '/Times-Bold', '/Times-Italic'}, fonts)
        self.assertIn('/Times-Roman', fonts)
        box = reader.pages[1].mediabox
        self.assertEqual((round(float(box.width)), round(float(box.height))), (595, 842))  # A4
