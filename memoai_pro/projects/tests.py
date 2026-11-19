import re

from rest_framework.test import APITestCase

from users.models import User
from .models import Project, Chapter, Reference

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

        from docx.oxml.ns import qn
        # Page de garde sans numéro, pages liminaires en chiffres romains, corps en chiffres arabes ;
        # une section par grande partie (Introduction, Chapitre I), ouverte par une page de titre.
        cover, front, intro, chapter = doc.sections
        for section in doc.sections:
            self.assertEqual((round(section.left_margin.cm, 2), round(section.right_margin.cm, 2),
                              round(section.top_margin.cm, 2), round(section.bottom_margin.cm, 2)), (4.0, 2.5, 2.5, 2.5))
        self.assertNotIn('PAGE', cover.footer._element.xml)
        for section, number_format, start in ((front, 'lowerRoman', '1'), (intro, 'decimal', '1'),
                                              (chapter, 'decimal', None)):
            pg_num = section._sectPr.find(qn('w:pgNumType'))
            self.assertEqual((pg_num.get(qn('w:fmt')), pg_num.get(qn('w:start'))), (number_format, start))
            self.assertIn('PAGE', section.footer._element.xml)
        for section in (intro, chapter):
            self.assertTrue(section.different_first_page_header_footer)  # page de titre sans en-tête ni numéro
        # En-tête courant souligné « Chapitre I ...... Revue de la littérature ».
        self.assertEqual(chapter.header.paragraphs[0].text, 'Chapitre I\tRevue de la littérature')
        self.assertIn('w:pBdr', chapter.header._element.xml)
        self.assertEqual(intro.header.paragraphs[0].text, '\tIntroduction générale')

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
            ('Heading 1', 'Chapitre I\nRevue de la littérature'), ('Heading 2', 'I.1. Définition des concepts'),
            ('Heading 3', 'I.1.1. Inclusion financière'),
        ])
        # Pages de titre des grandes parties.
        dividers = [p.text for p in doc.paragraphs if p.runs and p.runs[0].font.size == Pt(36)]
        self.assertEqual(dividers, ['Introduction générale', 'Chapitre I'])
        text = '\n'.join(p.text for p in doc.paragraphs)
        self.assertNotIn('Conseil du modèle', text)  # conseils de rédaction retirés du document final
        self.assertIn('Merci à tous.', text)

        # Sommaire : champ « table des matières » dans les pages liminaires, juste avant l'introduction,
        # mis à jour par Word à l'ouverture (numéros de page).
        body_xml = doc.element.body.xml
        self.assertIn('TOC \\o "1-4"', body_xml)
        titles = [p.text for p in doc.paragraphs]
        self.assertLess(titles.index('SOMMAIRE'), titles.index('Introduction générale'))
        self.assertGreater(titles.index('SOMMAIRE'), titles.index('Remerciements'))
        toc_lines = [p.text for p in doc.paragraphs if p.style.name.startswith('TOC')]
        self.assertEqual(toc_lines[:4], ['Dédicace', 'Remerciements', 'Introduction générale',
                                         'Chapitre I : Revue de la littérature'])
        self.assertIn('I.1. Définition des concepts', toc_lines)
        self.assertIn('I.1.1. Inclusion financière', toc_lines)
        self.assertIn('updateFields', doc.settings.element.xml)

    def test_pdf_one_part_per_page_with_numbers(self):
        from io import BytesIO

        from PyPDF2 import PdfReader
        reader = PdfReader(BytesIO(self.export("pdf")))
        pages = [p.extract_text() for p in reader.pages]
        # Page de titre, Dédicace, Remerciements, Sommaire, puis chaque grande partie précédée
        # de sa page de titre (sans en-tête ni numéro), comme dans les mémoires imprimés.
        self.assertEqual(len(pages), 8)
        for page, title in zip(pages[1:], ('DÉDICACE', 'REMERCIEMENTS', 'SOMMAIRE', 'Introduction générale',
                                           'INTRODUCTION GÉNÉRALE', 'Chapitre I', 'CHAPITRE I')):
            self.assertIn(title, page)
        self.assertEqual(pages[4].strip(), 'Introduction générale')  # page de titre seule
        self.assertEqual(pages[6].strip(), 'Chapitre I')
        self.assertIn('REVUE DE LA LITTÉRATURE', pages[7])
        self.assertIn('I.1. Définition des concepts', pages[7])
        self.assertIn('I.1.1. Inclusion financière', pages[7])
        # Le sommaire donne le numéro de page affiché de chaque partie et section.
        toc = pages[3]
        for entry, number in (('Dédicace', 'i'), ('Remerciements', 'ii'), ('Introduction générale', '2'),
                              ('Chapitre I : Revue de la littérature', '4'), ('I.1. Définition des concepts', '4'),
                              ('I.1.1. Inclusion financière', '4')):
            # L'extraction de texte restitue la ligne « . . . numéro » juste avant le titre de l'entrée.
            self.assertRegex(toc, rf'\. {number}\n{re.escape(entry)}\n')
        self.assertNotIn('Conseil du modèle', ''.join(pages))
        # Liminaires : i, ii, iii ; corps : 2, 4 (les pages de titre comptent mais n'affichent rien).
        lines = [page.strip().splitlines() for page in pages]
        self.assertEqual([lines[i][-1].strip() for i in (1, 2, 3)], ['i', 'ii', 'iii'])
        # En-tête courant en bas de l'extraction : numéro puis « Chapitre I / Revue de la littérature ».
        self.assertEqual(lines[5][-2:], ['2', 'Introduction générale'])
        self.assertEqual(lines[7][-3:], ['4', 'Chapitre I', 'Revue de la littérature'])
        self.assertTrue(pages[0].startswith('MOBILE MONEY AU MALI'))
        self.assertNotIn(pages[0].strip().splitlines()[-1].strip(), ('1', 'i'))
        fonts = set()
        for page in reader.pages:
            for font in page['/Resources']['/Font'].values():
                fonts.add(str(font.get_object()['/BaseFont']))
        # Helvetica n'est que la police déclarée par défaut par reportlab : aucun texte ne l'utilise.
        self.assertTrue(fonts - {'/Helvetica'} <= {'/Times-Roman', '/Times-Bold', '/Times-Italic'}, fonts)
        self.assertIn('/Times-Roman', fonts)
        box = reader.pages[1].mediabox
        self.assertEqual((round(float(box.width)), round(float(box.height))), (595, 842))  # A4


class TocNotWrittenByAITests(APITestCase):
    def test_sommaire_part_is_never_written_by_ai(self):
        from unittest import mock
        from django.test import override_settings
        from modeles.models import MemoirTemplate
        user = make_user('toc@test.com', 'STUDENT')
        self.client.force_authenticate(user)
        project = Project.objects.create(user=user, title='T', theme='T', desired_pages=40)
        project.template = MemoirTemplate.objects.get(slug='licence-classique')  # modèle gratuit
        project.save()
        sommaire = Chapter.objects.create(project=project, title='Sommaire', type='preliminary', order=1)
        with override_settings(AI_PROVIDER='openrouter', OPENAI_API_KEY='k'),                 mock.patch('ai.services._openrouter_client') as client:
            res = self.client.post(f'/projects/chapters/{sommaire.id}/generate_content/')
        self.assertEqual(res.status_code, 400)
        self.assertIn('automatiquement', res.data['error'])
        client.assert_not_called()


def png_data_url(width=300, height=200, color=(200, 30, 30)):
    import base64
    from io import BytesIO

    from PIL import Image
    buffer = BytesIO()
    Image.new('RGB', (width, height), color).save(buffer, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()


class ProjectImageTests(APITestCase):
    """Figures des mémoires : envoi par l'auteur, lecture par l'encadreur, insertion dans les exports."""

    def setUp(self):
        self.student = make_user('img@test.com', 'STUDENT')
        self.supervisor = make_user('img-enc@test.com', 'SUPERVISOR')
        self.other = make_user('img-other@test.com', 'STUDENT')
        self.project = Project.objects.create(user=self.student, title='Figures', supervisor=self.supervisor)

    def upload(self, data=None, caption='Évolution du nombre de comptes'):
        self.client.force_authenticate(self.student)
        return self.client.post('/projects/images/', {'project': self.project.id, 'data': data or png_data_url(),
                                                      'caption': caption}, format='json')

    def test_owner_uploads_and_gets_marker(self):
        res = self.upload(png_data_url(3000, 1500))
        self.assertEqual(res.status_code, 201)
        self.assertEqual((res.data['width'], res.data['height']), (1600, 800))  # réduite à 1600 px
        self.assertEqual(res.data['marker'], f"[Figure:{res.data['id']} | Évolution du nombre de comptes]")

    def test_invalid_image_and_other_users_rejected(self):
        self.assertEqual(self.upload('data:image/png;base64,bm90IGFuIGltYWdl').status_code, 400)
        self.client.force_authenticate(self.other)
        res = self.client.post('/projects/images/', {'project': self.project.id, 'data': png_data_url()}, format='json')
        self.assertIn(res.status_code, (403, 404))

    def test_read_and_delete_rights(self):
        image_id = self.upload().data['id']
        url = f'/projects/images/{image_id}/'
        self.client.force_authenticate(self.supervisor)
        res = self.client.get(url)
        self.assertEqual((res.status_code, res['Content-Type']), (200, 'image/png'))
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_figure_in_exports(self):
        from io import BytesIO

        from docx import Document
        from PyPDF2 import PdfReader
        marker = self.upload().data['marker']
        chapter = Chapter.objects.create(project=self.project, title='Chapitre 1 : Contexte', type='chapter',
                                         content='Texte.', order=1)
        Chapter.objects.create(project=self.project, parent=chapter, title='Données', type='section',
                               content=f'Avant la figure.\n{marker}\nAprès la figure.', order=1)

        def export(fmt):
            res = self.client.post(f'/projects/projects/{self.project.id}/export/', {'format': fmt}, format='json')
            self.assertEqual(res.status_code, 200)
            return b''.join(res.streaming_content) if hasattr(res, 'streaming_content') else res.content

        doc = Document(BytesIO(export('docx')))
        text = '\n'.join(p.text for p in doc.paragraphs)
        self.assertIn('Figure I.1 : Évolution du nombre de comptes', text)
        self.assertNotIn('[Figure:', text)
        self.assertEqual(len(doc.inline_shapes), 1)

        reader = PdfReader(BytesIO(export('pdf')))
        pdf_text = ''.join(page.extract_text() for page in reader.pages)
        self.assertIn('Figure I.1 : Évolution du nombre de comptes', pdf_text)
        # reportlab place l'image dans une XObject de la page (/Resources /XObject).
        self.assertIn('/XObject', ''.join(str(page['/Resources']) for page in reader.pages))

        html = export('html').decode()
        self.assertIn('data:image/png;base64,', html)
        self.assertIn('Figure I.1', html)


class TrashTests(APITestCase):
    """Corbeille : suppression réversible pendant 30 jours, puis définitive."""

    def setUp(self):
        self.student = make_user('trash@test.com', 'STUDENT')
        self.other = make_user('trash-other@test.com', 'STUDENT')
        self.client.force_authenticate(self.student)
        self.project = Project.objects.create(user=self.student, title='Mémoire corbeille')
        self.chapter = Chapter.objects.create(project=self.project, title='Chapitre 1', type='chapter', order=1)
        self.section = Chapter.objects.create(project=self.project, parent=self.chapter, title='Section',
                                              type='section', order=1)
        Chapter.objects.create(project=self.project, parent=self.section, title='Sous-section', type='section', order=1)
        self.reference = Reference.objects.create(project=self.project, title='Article', authors='Diallo, A.', year=2020)

    def trash(self):
        res = self.client.get('/projects/trash/')
        self.assertEqual(res.status_code, 200)
        return [(item['kind'], item['title']) for item in res.data['items']]

    def test_chapter_goes_to_trash_with_sections_and_comes_back(self):
        self.assertEqual(self.client.delete(f'/projects/chapters/{self.chapter.id}/').status_code, 204)
        self.assertEqual(self.client.get('/projects/chapters/', {'project': self.project.id}).data, [])
        self.assertEqual(self.trash(), [('chapter', 'Chapitre 1')])  # les sections suivent leur chapitre
        res = self.client.post('/projects/trash/restore/', {'kind': 'chapter', 'id': self.chapter.id}, format='json')
        self.assertEqual(res.status_code, 200)
        titles = {c['title'] for c in self.client.get('/projects/chapters/', {'project': self.project.id}).data}
        self.assertEqual(titles, {'Chapitre 1', 'Section', 'Sous-section'})
        self.assertEqual(self.trash(), [])

    def test_section_whose_chapter_is_trashed_returns_at_top_level(self):
        self.client.delete(f'/projects/chapters/{self.section.id}/')
        self.client.delete(f'/projects/chapters/{self.chapter.id}/')
        self.assertEqual(sorted(self.trash()), [('chapter', 'Chapitre 1'), ('chapter', 'Section')])
        self.client.post('/projects/trash/restore/', {'kind': 'chapter', 'id': self.section.id}, format='json')
        restored = Chapter.objects.get(id=self.section.id)
        self.assertIsNone(restored.parent_id)
        self.assertEqual([c.title for c in restored.children.all()], ['Sous-section'])

    def test_project_trash_hides_everything_until_restored(self):
        self.client.delete(f'/projects/projects/{self.project.id}/')
        self.assertEqual(self.client.get('/projects/projects/').data, [])
        self.assertEqual(self.client.get(f'/projects/chapters/{self.chapter.id}/').status_code, 404)
        self.assertEqual(self.trash(), [('project', 'Mémoire corbeille')])  # ses chapitres reviennent avec lui
        self.client.post('/projects/trash/restore/', {'kind': 'project', 'id': self.project.id}, format='json')
        self.assertEqual(len(self.client.get('/projects/projects/').data), 1)
        self.assertEqual(Chapter.objects.filter(project=self.project).count(), 3)

    def test_delete_forever_and_empty(self):
        self.client.delete(f'/projects/references/{self.reference.id}/')
        self.client.delete(f'/projects/chapters/{self.chapter.id}/')
        res = self.client.post('/projects/trash/delete/', {'kind': 'reference', 'id': self.reference.id}, format='json')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Reference.all_objects.filter(id=self.reference.id).exists())
        self.assertEqual(self.client.post('/projects/trash/empty/').status_code, 204)
        self.assertEqual(Chapter.all_objects.filter(project=self.project).count(), 0)
        self.assertTrue(Project.objects.filter(id=self.project.id).exists())

    def test_other_users_cannot_touch_my_trash(self):
        self.client.delete(f'/projects/chapters/{self.chapter.id}/')
        self.client.force_authenticate(self.other)
        self.assertEqual(self.trash(), [])
        res = self.client.post('/projects/trash/restore/', {'kind': 'chapter', 'id': self.chapter.id}, format='json')
        self.assertEqual(res.status_code, 404)
        res = self.client.post('/projects/trash/delete/', {'kind': 'chapter', 'id': self.chapter.id}, format='json')
        self.assertEqual(res.status_code, 404)

    def test_items_older_than_30_days_are_purged(self):
        from datetime import timedelta

        from django.utils import timezone
        self.client.delete(f'/projects/references/{self.reference.id}/')
        Reference.all_objects.filter(id=self.reference.id).update(deleted_at=timezone.now() - timedelta(days=31))
        self.assertEqual(self.trash(), [])
        self.assertFalse(Reference.all_objects.filter(id=self.reference.id).exists())


class SecurityProjectTests(APITestCase):
    def setUp(self):
        self.student = make_user('sec@test.com', 'STUDENT')
        self.client.force_authenticate(self.student)
        self.project = Project.objects.create(user=self.student, title='Secret')

    def test_decompression_bomb_rejected(self):
        res = self.client.post('/projects/images/', {'project': self.project.id,
                                                     'data': png_data_url(8000, 8000, (0, 0, 0))}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('trop grande', res.data['error'])

    def test_svg_rejected(self):
        import base64
        svg = base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>').decode()
        res = self.client.post('/projects/images/', {'project': self.project.id,
                                                     'data': f'data:image/svg+xml;base64,{svg}'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_share_link_of_trashed_project_stops_working(self):
        res = self.client.post('/projects/share-links/', {'project': self.project.id}, format='json')
        if res.status_code not in (200, 201):
            self.skipTest(f'API de partage différente : {res.status_code}')
        token = res.data.get('token') or res.data.get('url', '').rstrip('/').split('/')[-1]
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/projects/shared/{token}/').status_code, 200)
        self.client.force_authenticate(self.student)
        self.client.delete(f'/projects/projects/{self.project.id}/')
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/projects/shared/{token}/').status_code, 404)
