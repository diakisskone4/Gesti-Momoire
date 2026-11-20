"""Export d'un mémoire présenté comme un mémoire universitaire imprimé.

- Page de garde, puis pages liminaires (dédicace, remerciements, sigles, listes, résumé, sommaire)
  numérotées en chiffres romains.
- Chaque grande partie du corps (introduction, chapitres, conclusion, bibliographie, annexes) est
  précédée d'une page de titre (« Introduction », « Chapitre I »...), sans en-tête ni numéro.
- Chapitres en chiffres romains : « Chapitre I » puis le titre ; sections numérotées I.1., I.1.1., I.1.2.1.
- En-tête courant « Chapitre I ............ Titre du chapitre », souligné ; numéro de page en bas.
- Figures insérées dans le texte par une ligne [Figure:ID | légende], centrées, légende numérotée
  par chapitre : « Figure I.1 : légende ».
"""
import base64
import re
import unicodedata
from dataclasses import dataclass, field
from html import escape
from io import BytesIO

from . import document_format as fmt

_CHAPTER = re.compile(r'^\s*chapitre\s+(\d+|[ivxlcdm]+)\b\s*[:.\-–—]?\s*(.*)$', re.IGNORECASE)
_LEADING_NUMBER = re.compile(r'^\s*(?:[IVXLC]+\.)?\d+(?:\.\d+)*\.?\s+')
FIGURE_LINE = re.compile(r'^\[\s*Figure\s*:\s*(\d+)\s*(?:\|\s*(.*?))?\s*\]$', re.IGNORECASE)
MAX_FIGURE_WIDTH_CM = fmt.TEXT_WIDTH_CM
MAX_FIGURE_HEIGHT_CM = 11.0


def _plain(text):
    return unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode().lower()


def is_bibliography(chapter):
    title = _plain(chapter.title)
    return chapter.type == 'back' and ('bibliograph' in title or 'reference' in title)


@dataclass
class Part:
    """Une partie, une section ou une sous-section du mémoire, telle qu'elle sera imprimée."""
    level: int
    chapter: object
    lines: list                 # lignes du titre (« Chapitre I », « Synthèse bibliographique... »)
    toc_text: str               # texte dans le sommaire
    matter: str                 # fmt.FRONT_MATTER (i, ii...) ou fmt.MAIN_MATTER (1, 2...)
    is_toc: bool = False
    divider: str = ''           # titre de la page de séparation (corps du mémoire)
    header: tuple = None        # en-tête courant (gauche, droite)
    figure_prefix: str = None   # « I » : figures I.1, I.2...


def build_layout(outline):
    """Plan d'impression : numérotation des chapitres (I, II...) et des sections (I.1., I.1.1....)."""
    parts = []
    prefix = None
    counters = [0] * 8
    matter = fmt.MAIN_MATTER
    for level, chapter in outline:
        if level == 1:
            counters = [0] * 8
            if fmt.is_toc(chapter):
                parts.append(Part(1, chapter, [], '', fmt.FRONT_MATTER, is_toc=True))
                prefix = None
                continue
            matter = fmt.numbering_of(1, chapter)
            match = _CHAPTER.match(chapter.title or '')
            if match and matter == fmt.MAIN_MATTER:
                number = match.group(1)
                prefix = fmt.to_roman(int(number)).upper() if number.isdigit() else number.upper()
                label = f'Chapitre {prefix}'
                rest = match.group(2).strip()
                parts.append(Part(1, chapter, [label] + ([rest] if rest else []),
                                  f'{label} : {rest}' if rest else label, matter,
                                  divider=label, header=(label, rest or label), figure_prefix=prefix))
            else:
                prefix = None
                title = chapter.title
                parts.append(Part(1, chapter, [title], title, matter,
                                  divider=title if matter == fmt.MAIN_MATTER else '',
                                  header=('', title) if matter == fmt.MAIN_MATTER else None))
            continue
        title = chapter.title
        if prefix:  # sections d'un chapitre numéroté : I.1., I.1.1., ...
            depth = min(level - 2, len(counters) - 1)
            counters[depth] += 1
            for i in range(depth + 1, len(counters)):
                counters[i] = 0
            number = '.'.join([prefix] + [str(c) for c in counters[:depth + 1]])
            title = f'{number}. {_LEADING_NUMBER.sub("", title).strip()}'
        parts.append(Part(level, chapter, [title], title, matter, figure_prefix=prefix))
    return parts


def content_blocks(content):
    """Blocs du texte d'un chapitre : ('figure', id, légende) ou ('text', texte, élément_de_liste)."""
    blocks = []
    for text, is_item in fmt.body_paragraphs(content):
        match = FIGURE_LINE.match(text)
        if match:
            blocks.append(('figure', int(match.group(1)), (match.group(2) or '').strip()))
        else:
            blocks.append(('text', text, is_item))
    return blocks


def figure_ids(outline):
    return {block[1] for _, chapter in outline for block in content_blocks(chapter.content) if block[0] == 'figure'}


class FigureNumbering:
    """« Figure I.1 », « Figure I.2 »... par chapitre ; « Figure 1 », « Figure 2 »... hors chapitre numéroté."""

    def __init__(self):
        self.counts = {}

    def next(self, prefix):
        key = prefix or ''
        self.counts[key] = self.counts.get(key, 0) + 1
        return f'Figure {prefix}.{self.counts[key]}' if prefix else f'Figure {self.counts[key]}'


def _figure_size_cm(image):
    """Taille d'affichage (cm) : taille naturelle à 96 ppp, réduite pour tenir dans la page."""
    width = image.width * 2.54 / 96
    height = image.height * 2.54 / 96
    scale = min(1.0, MAX_FIGURE_WIDTH_CM / width, MAX_FIGURE_HEIGHT_CM / height)
    return width * scale, height * scale


@dataclass
class ExportData:
    project: object
    parts: list
    references: list            # références déjà mises en forme
    cover: tuple = None         # (modèle, données) : page de garde du modèle utilisé, ou None
    meta_lines: list = field(default_factory=list)
    images: dict = field(default_factory=dict)

    @property
    def bibliography_part(self):
        return next((p for p in self.parts if p.level == 1 and is_bibliography(p.chapter)), None)

    def toc_entries(self):
        entries = [(p.level, p.toc_text) for p in self.parts
                   if not p.is_toc and p.level <= fmt.TOC_DEPTH]
        if self.references and self.bibliography_part is None:
            entries.append((1, 'Bibliographie'))
        return entries


# ------------------------------------------------------------------ Word

def render_docx(data):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt

    doc = Document()
    fmt.setup_docx(doc)
    figures = FigureNumbering()

    if data.cover:
        from modeles.cover_render import add_docx_cover
        add_docx_cover(doc, *data.cover)  # page de garde du modèle (même design que l'aperçu)
    else:
        fmt.centered_docx_paragraph(doc, '', 12, space_after_pt=150)
        fmt.centered_docx_paragraph(doc, data.project.title.upper(), 20, bold=True, space_after_pt=36)
        for line in data.meta_lines:
            fmt.centered_docx_paragraph(doc, line, 12, space_after_pt=6)

    state = {'numbering': None, 'first_main': True, 'toc_done': not data.toc_entries()}

    def front_section():
        if state['numbering'] == fmt.FRONT_MATTER:
            return False
        fmt.start_docx_part(doc, fmt.FRONT_MATTER, restart=True)
        state['numbering'] = fmt.FRONT_MATTER
        return True

    def insert_toc():
        new = front_section()
        fmt.add_docx_toc(doc, data.toc_entries(), page_break_before=not new)
        state['toc_done'] = True

    def heading(lines, level, page_break=None):
        paragraph = doc.add_heading('', level=min(level, 4))
        for i, line in enumerate(lines):
            run = paragraph.add_run(line)
            if i < len(lines) - 1:
                run.add_break()
        if page_break is not None:
            paragraph.paragraph_format.page_break_before = page_break
        return paragraph

    def start_main(divider, header):
        if not state['toc_done']:
            insert_toc()
        fmt.start_docx_part(doc, fmt.MAIN_MATTER, restart=state['first_main'], header=header, title_page=True)
        state['first_main'] = False
        state['numbering'] = fmt.MAIN_MATTER
        fmt.add_docx_divider(doc, divider)

    def add_figure(image_id, caption, prefix):
        image = data.images.get(image_id)
        if image is None:
            doc.add_paragraph(f'[Image {image_id} introuvable]')
            return
        width, _ = _figure_size_cm(image)
        picture = doc.add_paragraph()
        pf = picture.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf.first_line_indent = Cm(0)
        pf.keep_with_next = True
        pf.line_spacing = 1
        picture.add_run().add_picture(BytesIO(bytes(image.data)), width=Cm(width))
        legend = doc.add_paragraph()
        lf = legend.paragraph_format
        lf.alignment = WD_ALIGN_PARAGRAPH.CENTER
        lf.first_line_indent = Cm(0)
        lf.space_after = Pt(12)
        label = legend.add_run(f'{figures.next(prefix)} : ' if caption else figures.next(prefix))
        label.bold = label.italic = True
        label.font.size = Pt(11)
        if caption:
            text = legend.add_run(caption)
            text.italic = True
            text.font.size = Pt(11)

    def add_body(part):
        for block in content_blocks(part.chapter.content):
            if block[0] == 'figure':
                add_figure(block[1], block[2], part.figure_prefix)
                continue
            _, text, is_item = block
            paragraph = doc.add_paragraph(text)
            if is_item:
                pf = paragraph.paragraph_format
                pf.first_line_indent = Cm(-0.5)
                pf.left_indent = Cm(fmt.FIRST_LINE_INDENT_CM)
                pf.alignment = WD_ALIGN_PARAGRAPH.LEFT

    def add_references():
        for reference in data.references:
            paragraph = doc.add_paragraph(reference)
            pf = paragraph.paragraph_format
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.left_indent = Cm(1)
            pf.first_line_indent = Cm(-1)

    for part in data.parts:
        if part.is_toc:
            if not state['toc_done']:
                insert_toc()
            continue
        if part.level == 1 and part.matter == fmt.MAIN_MATTER:
            start_main(part.divider, part.header)
            heading(part.lines, 1)  # le style « Titre 1 » commence une nouvelle page après la page de titre
        elif part.level == 1:
            new = front_section()
            heading(part.lines, 1, page_break=False if new else None)
        else:
            heading(part.lines, part.level)
        add_body(part)
        if part is data.bibliography_part:
            add_references()

    if not state['toc_done']:
        insert_toc()
    if data.references and data.bibliography_part is None:
        start_main('Bibliographie', ('', 'Bibliographie'))
        heading(['Bibliographie'], 1)
        add_references()

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


# ------------------------------------------------------------------ PDF

def render_pdf(data):
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, Spacer

    buffer = BytesIO()
    MemoirDocTemplate, NumberingStart, HeaderStart, DividerMark = fmt.pdf_classes()
    doc = MemoirDocTemplate(buffer, pagesize=A4, title=data.project.title, author=data.project.user.full_name,
                            **fmt.pdf_margins())
    body, item, headings = fmt.pdf_styles()
    divider_style = ParagraphStyle('separation', fontName='Times-Bold', fontSize=fmt.DIVIDER_SIZE,
                                   leading=fmt.DIVIDER_SIZE * 1.25, alignment=TA_CENTER)
    legend_style = ParagraphStyle('legende', fontName='Times-Italic', fontSize=11, leading=14, alignment=TA_CENTER,
                                  spaceBefore=4, spaceAfter=12)
    reference_style = ParagraphStyle('reference', parent=body, alignment=0, firstLineIndent=-1 * cm, leftIndent=1 * cm)
    figures = FigureNumbering()

    def centered(text, size, font='Times-Roman', space_after=0):
        return Paragraph(escape(text), ParagraphStyle(f'c-{size}-{font}', fontName=font, fontSize=size,
                                                      leading=size * 1.35, alignment=TA_CENTER, spaceAfter=space_after))

    story = []
    if data.cover:
        from modeles.cover_render import pdf_cover_flowable
        story.append(pdf_cover_flowable(*data.cover))  # page de garde du modèle (même design que l'aperçu)
    else:
        story.append(Spacer(1, 6 * cm))
        story.append(centered(data.project.title.upper(), 20, 'Times-Bold', space_after=36))
        story += [centered(line, 12, space_after=6) for line in data.meta_lines]

    state = {'numbering': None, 'toc_done': not data.toc_entries()}

    def new_page(number_format, header):
        story.append(PageBreak())
        if state['numbering'] != number_format:
            story.append(NumberingStart(number_format))
            state['numbering'] = number_format
        story.append(HeaderStart(header))

    def insert_toc():
        new_page(fmt.FRONT_MATTER, None)
        story.append(Paragraph(fmt.TOC_TITLE.upper(), headings[1]))
        story.append(fmt.pdf_toc(doc))
        state['toc_done'] = True

    def heading(lines, level, toc_text):
        text = '<br/>'.join(escape(line.upper() if level == 1 else line) for line in lines)
        paragraph = Paragraph(text, headings[min(level, 3)])
        if level <= fmt.TOC_DEPTH:
            paragraph.toc_level = level
            paragraph.toc_text = toc_text
        story.append(paragraph)

    def start_main(divider, header):
        if not state['toc_done']:
            insert_toc()
        new_page(fmt.MAIN_MATTER, header)
        story.extend([DividerMark(), Spacer(1, 7.5 * cm), Paragraph(escape(divider), divider_style), PageBreak()])

    def add_figure(image_id, caption, prefix):
        image = data.images.get(image_id)
        if image is None:
            story.append(Paragraph(escape(f'[Image {image_id} introuvable]'), body))
            return
        width, height = _figure_size_cm(image)
        picture = Image(BytesIO(bytes(image.data)), width=width * cm, height=height * cm)
        picture.hAlign = 'CENTER'
        label = figures.next(prefix)
        legend = f'<b>{escape(label)} :</b> {escape(caption)}' if caption else f'<b>{escape(label)}</b>'
        story.append(KeepTogether([Spacer(1, 6), picture, Paragraph(legend, legend_style)]))

    def add_body(part):
        for block in content_blocks(part.chapter.content):
            if block[0] == 'figure':
                add_figure(block[1], block[2], part.figure_prefix)
            else:
                story.append(Paragraph(escape(block[1]), item if block[2] else body))

    for part in data.parts:
        if part.is_toc:
            if not state['toc_done']:
                insert_toc()
            continue
        if part.level == 1 and part.matter == fmt.MAIN_MATTER:
            start_main(part.divider, part.header)
        elif part.level == 1:
            new_page(fmt.FRONT_MATTER, None)
        heading(part.lines, part.level, part.toc_text)
        add_body(part)
        if part is data.bibliography_part:
            story.extend(Paragraph(escape(r), reference_style) for r in data.references)

    if not state['toc_done']:
        insert_toc()
    if data.references and data.bibliography_part is None:
        start_main('Bibliographie', ('', 'Bibliographie'))
        heading(['Bibliographie'], 1, 'Bibliographie')
        story.extend(Paragraph(escape(r), reference_style) for r in data.references)

    doc.multiBuild(story)  # plusieurs passes : le sommaire reçoit les numéros de page définitifs
    return buffer.getvalue()


# ------------------------------------------------------------------ HTML

def render_html(data, cover_css='', cover_html=''):
    figures = FigureNumbering()
    body = [cover_html] if cover_html else (
        [f'<p class="titre-page" style="font-size:20pt;font-weight:bold;margin-top:6cm">'
         f'{escape(data.project.title.upper())}</p>']
        + [f'<p class="meta">{escape(line)}</p>' for line in data.meta_lines])
    entries = data.toc_entries()
    toc_html = ('<h2 class="chapitre">Sommaire</h2><ul class="sommaire">'
                + ''.join(f'<li class="niveau-{lvl}">{escape(t)}</li>' for lvl, t in entries) + '</ul>')
    toc_done = not entries

    def figure_html(image_id, caption, prefix):
        image = data.images.get(image_id)
        if image is None:
            return f'<p>[Image {image_id} introuvable]</p>'
        src = f'data:{image.content_type};base64,{base64.b64encode(bytes(image.data)).decode()}'
        width, _ = _figure_size_cm(image)
        label = figures.next(prefix)
        legend = f'<b>{escape(label)} :</b> {escape(caption)}' if caption else f'<b>{escape(label)}</b>'
        return (f'<figure><img src="{src}" alt="{escape(caption or label)}" style="width:{width:.1f}cm">'
                f'<figcaption>{legend}</figcaption></figure>')

    for part in data.parts:
        if part.is_toc or (part.level == 1 and part.matter == fmt.MAIN_MATTER and not toc_done):
            if not toc_done:
                body.append(toc_html)
                toc_done = True
            if part.is_toc:
                continue
        if part.level == 1:
            if part.divider:
                body.append(f'<div class="separation">{escape(part.divider)}</div>')
            body.append(f'<h2 class="chapitre">{"<br>".join(escape(line) for line in part.lines)}</h2>')
        else:
            tag = f'h{min(part.level + 1, 6)}'
            body.append(f'<{tag}>{escape(part.lines[0])}</{tag}>')
        for block in content_blocks(part.chapter.content):
            if block[0] == 'figure':
                body.append(figure_html(block[1], block[2], part.figure_prefix))
            else:
                css = ' class="item"' if block[2] else ''
                body.append(f'<p{css}>{escape(block[1])}</p>')
        if part is data.bibliography_part:
            body += [f'<p class="ref">{escape(r)}</p>' for r in data.references]
    if not toc_done:
        body.append(toc_html)
    if data.references and data.bibliography_part is None:
        body.append('<div class="separation">Bibliographie</div><h2 class="chapitre">Bibliographie</h2>')
        body += [f'<p class="ref">{escape(r)}</p>' for r in data.references]

    css = (fmt.HTML_CSS + cover_css
           + '.separation{font-size:36pt;font-weight:bold;text-align:center;padding:9cm 0 0;min-height:20cm;'
             'break-before:page;page-break-before:always}'
           + '.separation + h2.chapitre{break-before:page;page-break-before:always}'
           + 'figure{margin:12pt auto;text-align:center;break-inside:avoid}figure img{max-width:100%}'
           + 'figcaption{font-style:italic;font-size:11pt;margin-top:4pt}'
           + '.sommaire{list-style:none;padding:0}.sommaire .niveau-1{font-weight:bold;margin-top:6pt}'
           + '.sommaire .niveau-2{padding-left:.6cm}.sommaire .niveau-3{padding-left:1.2cm}')
    return ('<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">'
            f'<title>{escape(data.project.title)}</title><style>{css}</style></head><body>'
            + ''.join(body) + '</body></html>')
