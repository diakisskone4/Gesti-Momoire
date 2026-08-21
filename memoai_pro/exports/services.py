# exports/services.py
import os
import tempfile
import markdown
import re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from django.conf import settings
from django.core.files.storage import default_storage
import subprocess  # pour LaTeX
import zipfile

class ExportService:
    @staticmethod
    def export(project, format, output_path=None):
        if format == 'docx':
            return ExportService._export_docx(project, output_path)
        elif format == 'pdf':
            return ExportService._export_pdf(project, output_path)
        elif format == 'latex':
            return ExportService._export_latex(project, output_path)
        elif format == 'odt':
            return ExportService._export_odt(project, output_path)
        elif format == 'html':
            return ExportService._export_html(project, output_path)
        elif format == 'epub':
            return ExportService._export_epub(project, output_path)
        raise ValueError("Format not supported")

    @staticmethod
    def _get_chapters_tree(project):
        chapters = project.chapters.filter(parent=None).order_by('order')
        return chapters

    @staticmethod
    def _build_content(project):
        """Retourne le contenu structuré pour tous les formats."""
        content = []
        # Page de garde
        content.append({'type': 'title', 'text': project.title})
        content.append({'type': 'subtitle', 'text': f"Auteur: {project.user.first_name} {project.user.last_name}"})
        content.append({'type': 'subtitle', 'text': f"Université: {project.university} - {project.faculty}"})
        content.append({'type': 'break'})
        # Table des matières (générée automatiquement)
        content.append({'type': 'toc'})
        content.append({'type': 'break'})
        # Chapitres
        for ch in project.chapters.filter(parent=None).order_by('order'):
            content.append({'type': 'chapter', 'title': ch.title, 'content': ch.content, 'level': 1})
            for sub in ch.children.all().order_by('order'):
                content.append({'type': 'chapter', 'title': sub.title, 'content': sub.content, 'level': 2})
                for subsub in sub.children.all().order_by('order'):
                    content.append({'type': 'chapter', 'title': subsub.title, 'content': subsub.content, 'level': 3})
        # Bibliographie
        content.append({'type': 'break'})
        content.append({'type': 'references', 'items': project.references.all()})
        return content

    # ---------- DOCX ----------
    @staticmethod
    def _export_docx(project, output_path=None):
        doc = Document()
        # Styles
        title_style = doc.styles['Title']
        title_style.font.size = Pt(24)
        heading1 = doc.styles['Heading 1']
        heading1.font.size = Pt(18)
        heading2 = doc.styles['Heading 2']
        heading2.font.size = Pt(14)
        normal = doc.styles['Normal']
        normal.font.size = Pt(12)
        # Titre
        doc.add_paragraph(project.title, style='Title').alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph(f"Auteur: {project.user.first_name} {project.user.last_name}", style='Normal').alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph(f"Université: {project.university}", style='Normal').alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_page_break()
        # Table des matières (placeholder)
        doc.add_heading('Table des matières', level=1)
        doc.add_paragraph('(À générer automatiquement dans Word)')
        doc.add_page_break()
        # Contenu
        for ch in project.chapters.filter(parent=None).order_by('order'):
            doc.add_heading(ch.title, level=1)
            doc.add_paragraph(ch.content)
            for sub in ch.children.all().order_by('order'):
                doc.add_heading(sub.title, level=2)
                doc.add_paragraph(sub.content)
                for subsub in sub.children.all().order_by('order'):
                    doc.add_heading(subsub.title, level=3)
                    doc.add_paragraph(subsub.content)
        # Bibliographie
        doc.add_page_break()
        doc.add_heading('Bibliographie', level=1)
        for ref in project.references.all():
            doc.add_paragraph(f"{ref.authors} ({ref.year}). {ref.title}. {ref.journal or ''} DOI: {ref.doi or ''}", style='Normal')
        # Sauvegarde
        if not output_path:
            output_path = tempfile.NamedTemporaryFile(suffix='.docx', delete=False).name
        doc.save(output_path)
        return output_path

    # ---------- PDF (ReportLab) ----------
    @staticmethod
    def _export_pdf(project, output_path=None):
        if not output_path:
            output_path = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        # Titre
        title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=24, alignment=1, spaceAfter=30)
        story.append(Paragraph(project.title, title_style))
        story.append(Paragraph(f"Auteur: {project.user.first_name} {project.user.last_name}", styles['Normal']))
        story.append(Spacer(1, 0.5*inch))
        # Chapitres
        for ch in project.chapters.filter(parent=None).order_by('order'):
            story.append(Paragraph(ch.title, styles['Heading1']))
            story.append(Paragraph(ch.content.replace('\n', '<br/>'), styles['Normal']))
            for sub in ch.children.all().order_by('order'):
                story.append(Paragraph(sub.title, styles['Heading2']))
                story.append(Paragraph(sub.content.replace('\n', '<br/>'), styles['Normal']))
        doc.build(story)
        return output_path

    # ---------- LaTeX ----------
    @staticmethod
    def _export_latex(project, output_path=None):
        if not output_path:
            output_path = tempfile.NamedTemporaryFile(suffix='.tex', delete=False).name
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\\documentclass[12pt,a4paper]{report}\n")
            f.write("\\usepackage[utf8]{inputenc}\n")
            f.write("\\usepackage[T1]{fontenc}\n")
            f.write("\\usepackage[french]{babel}\n")
            f.write("\\usepackage{graphicx}\n")
            f.write("\\title{" + project.title + "}\n")
            f.write("\\author{" + project.user.first_name + " " + project.user.last_name + "}\n")
            f.write("\\date{\\today}\n")
            f.write("\\begin{document}\n")
            f.write("\\maketitle\n")
            f.write("\\tableofcontents\n")
            f.write("\\newpage\n")
            for ch in project.chapters.filter(parent=None).order_by('order'):
                f.write(f"\\chapter{{{ch.title}}}\n")
                f.write(ch.content + "\n\n")
                for sub in ch.children.all().order_by('order'):
                    f.write(f"\\section{{{sub.title}}}\n")
                    f.write(sub.content + "\n\n")
                    for subsub in sub.children.all().order_by('order'):
                        f.write(f"\\subsection{{{subsub.title}}}\n")
                        f.write(subsub.content + "\n\n")
            f.write("\\bibliographystyle{plain}\n")
            f.write("\\bibliography{references}\n")
            f.write("\\end{document}\n")
        return output_path

    # ---------- HTML ----------
    @staticmethod
    def _export_html(project, output_path=None):
        if not output_path:
            output_path = tempfile.NamedTemporaryFile(suffix='.html', delete=False).name
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><title>{project.title}</title>
        <style>body{{max-width:800px;margin:auto;padding:20px;font-family:serif;}}
        h1{{font-size:24px;}} h2{{font-size:18px;}} h3{{font-size:14px;}}
        .cover{{text-align:center;margin-bottom:40px;}}
        </style>
        </head>
        <body>
        <div class="cover"><h1>{project.title}</h1>
        <p>Auteur: {project.user.first_name} {project.user.last_name}</p>
        <p>Université: {project.university}</p></div>
        """
        for ch in project.chapters.filter(parent=None).order_by('order'):
            html += f"<h1>{ch.title}</h1><div>{markdown.markdown(ch.content)}</div>"
            for sub in ch.children.all().order_by('order'):
                html += f"<h2>{sub.title}</h2><div>{markdown.markdown(sub.content)}</div>"
        html += "</body></html>"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return output_path

    # ---------- EPUB (simple) ----------
    @staticmethod
    def _export_epub(project, output_path=None):
        if not output_path:
            output_path = tempfile.NamedTemporaryFile(suffix='.epub', delete=False).name
        # On génère d'abord le HTML, puis on utilise pandoc ou ebooklib
        # Ici, utilisation simplifiée avec un zip (structure minimale)
        import zipfile
        import datetime
        epub_dir = tempfile.mkdtemp()
        # Créer mimetype
        with open(os.path.join(epub_dir, 'mimetype'), 'w') as f:
            f.write('application/epub+zip')
        # Créer META-INF
        os.makedirs(os.path.join(epub_dir, 'META-INF'), exist_ok=True)
        with open(os.path.join(epub_dir, 'META-INF', 'container.xml'), 'w') as f:
            f.write('''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>''')
        # Créer content.opf
        with open(os.path.join(epub_dir, 'content.opf'), 'w', encoding='utf-8') as f:
            f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId">
<metadata><dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">{project.title}</dc:title>
<dc:creator>{project.user.first_name} {project.user.last_name}</dc:creator>
<dc:language>fr</dc:language>
<dc:identifier id="BookId">{project.id}</dc:identifier>
<dc:date>{datetime.datetime.now().isoformat()}</dc:date>
</metadata>
<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="cover"/></spine>
</package>''')
        # Créer cover.xhtml
        with open(os.path.join(epub_dir, 'cover.xhtml'), 'w', encoding='utf-8') as f:
            f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{project.title}</title></head>
<body><h1>{project.title}</h1><p>Auteur: {project.user.first_name} {project.user.last_name}</p>
<p>Université: {project.university}</p></body></html>''')
        # Zipper
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(epub_dir):
                for f in files:
                    zf.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), epub_dir))
        import shutil
        shutil.rmtree(epub_dir)
        return output_path