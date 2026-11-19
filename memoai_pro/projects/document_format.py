"""Mise en page académique des mémoires exportés (Word, PDF, HTML).

Normes appliquées :
- Corps : Times New Roman 12 pt, noir, interligne 1,5, justifié, 6 pt avant/après,
  retrait de première ligne 1,25 cm.
- Titres : chapitre 16 pt gras MAJUSCULES centré ; section 14 pt gras ; sous-section 13 pt gras.
- Marges : gauche 4 cm, droite 2,5 cm, haut 2,5 cm, bas 2,5 cm.
- Pagination en bas de page, centrée, sauf sur la page de garde.
- Chaque partie de premier niveau (dédicace, remerciements, introduction, chapitres,
  conclusion, bibliographie...) commence sur une nouvelle page.
"""
import re

FONT = 'Times New Roman'
BODY_SIZE = 12
LINE_SPACING = 1.5
PARAGRAPH_SPACING = 6          # pt avant et après
FIRST_LINE_INDENT_CM = 1.25
HEADING_SIZES = {1: 16, 2: 14, 3: 13}  # chapitre, section, sous-section (et niveaux inférieurs)
DIVIDER_SIZE = 36  # titre des pages de séparation (« Chapitre I », « Introduction »...)
TEXT_WIDTH_CM = 21 - 4.0 - 2.5  # largeur du texte (A4 moins les marges)
MARGINS_CM = {'left': 4.0, 'right': 2.5, 'top': 2.5, 'bottom': 2.5}

# Conseils de rédaction laissés par les modèles : utiles dans l'éditeur, retirés du document final.
_ADVICE = re.compile(r'^\s*\[(Conseil du modèle|Sous-parties prévues)[^\]]*\]\s*$')
_LIST_ITEM = re.compile(r'^(•|-|\d+[.)])\s+')


def heading_size(level):
    return HEADING_SIZES.get(level, HEADING_SIZES[3])


def body_paragraphs(content):
    """Paragraphes du texte d'un chapitre : [(texte, est_un_élément_de_liste)], sans les conseils du modèle."""
    paragraphs = []
    for line in (content or '').split('\n'):
        line = line.strip()
        if line and not _ADVICE.match(line):
            paragraphs.append((line, bool(_LIST_ITEM.match(line))))
    return paragraphs


# ------------------------------------------------------------------ Word (python-docx)

def _set_run_fonts(element, size_pt=None, bold=None):
    """Times New Roman sur toutes les écritures (latin, asiatique, complexe), sans police de thème."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    rpr = element.get_or_add_rPr()
    fonts = rpr.find(qn('w:rFonts'))
    if fonts is None:
        fonts = OxmlElement('w:rFonts')
        rpr.insert(0, fonts)
    for attr in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
        fonts.attrib.pop(qn(attr), None)
    for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        fonts.set(qn(attr), FONT)


def setup_docx(doc):
    """Styles, marges et pagination d'un document Word."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    black = RGBColor(0, 0, 0)
    for section in doc.sections:
        section.left_margin = Cm(MARGINS_CM['left'])
        section.right_margin = Cm(MARGINS_CM['right'])
        section.top_margin = Cm(MARGINS_CM['top'])
        section.bottom_margin = Cm(MARGINS_CM['bottom'])

    normal = doc.styles['Normal']
    normal.font.name = FONT
    normal.font.size = Pt(BODY_SIZE)
    normal.font.color.rgb = black
    _set_run_fonts(normal.element)
    fmt = normal.paragraph_format
    fmt.line_spacing = LINE_SPACING
    fmt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    fmt.space_before = Pt(PARAGRAPH_SPACING)
    fmt.space_after = Pt(PARAGRAPH_SPACING)
    fmt.first_line_indent = Cm(FIRST_LINE_INDENT_CM)

    for level in (1, 2, 3, 4):
        style = doc.styles[f'Heading {level}']
        style.font.name = FONT
        style.font.size = Pt(heading_size(level))
        style.font.bold = True
        style.font.italic = False
        style.font.color.rgb = black
        style.font.all_caps = level == 1
        _set_run_fonts(style.element)
        hfmt = style.paragraph_format
        hfmt.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
        hfmt.first_line_indent = Cm(0)
        hfmt.line_spacing = 1.15
        hfmt.space_before = Pt(0 if level == 1 else 12)
        hfmt.space_after = Pt(18 if level == 1 else PARAGRAPH_SPACING)
        hfmt.keep_with_next = True
        # Chaque partie de premier niveau commence sur une nouvelle page.
        hfmt.page_break_before = level == 1

    # La première section (page de garde) n'a pas de numéro : les pages liminaires et le corps
    # du mémoire sont ouverts ensuite par start_docx_part(), chacun avec sa numérotation.


# Numérotation : pages liminaires (dédicace → liste des tableaux) en chiffres romains minuscules,
# corps du mémoire (introduction → annexes) en chiffres arabes, chacune repartant de 1.
FRONT_MATTER, MAIN_MATTER = 'lowerRoman', 'decimal'
# Éléments de w:sectPr situés après w:pgNumType (l'ordre est imposé par le format Word).
_SECTPR_AFTER_PGNUMTYPE = ('w:cols', 'w:formProt', 'w:vAlign', 'w:noEndnote', 'w:titlePg', 'w:textDirection',
                           'w:bidi', 'w:rtlGutter', 'w:docGrid', 'w:printerSettings')


def numbering_of(level, chapter):
    """Numérotation d'une partie de premier niveau : romaine pour les pages liminaires, arabe sinon."""
    return FRONT_MATTER if chapter.type == 'preliminary' else MAIN_MATTER


def _set_page_numbering(section, number_format, restart=True):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    sect_pr = section._sectPr
    pg_num = sect_pr.find(qn('w:pgNumType'))
    if pg_num is None:
        pg_num = OxmlElement('w:pgNumType')
        successor = next((el for tag in _SECTPR_AFTER_PGNUMTYPE if (el := sect_pr.find(qn(tag))) is not None), None)
        if successor is not None:
            successor.addprevious(pg_num)
        else:
            sect_pr.append(pg_num)
    pg_num.set(qn('w:fmt'), number_format)
    if restart:
        pg_num.set(qn('w:start'), '1')
    else:
        pg_num.attrib.pop(qn('w:start'), None)  # la numérotation continue depuis la section précédente


def _add_page_number_footer(section):
    """Numéro de page centré en bas (champ PAGE, mis à jour par Word)."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt
    footer = section.footer
    footer.is_linked_to_previous = False
    paragraph = footer.paragraphs[0]
    for child in list(paragraph._p):
        if child.tag != qn('w:pPr'):
            paragraph._p.remove(child)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    run = OxmlElement('w:r')
    text = OxmlElement('w:t')
    text.text = '1'
    run.append(text)
    field.append(run)
    paragraph._p.append(field)


# Éléments de w:pPr situés après w:pBdr (ordre imposé par le format Word).
_PPR_AFTER_PBDR = ('w:shd', 'w:tabs', 'w:suppressAutoHyphens', 'w:kinsoku', 'w:wordWrap', 'w:overflowPunct',
                   'w:topLinePunct', 'w:autoSpaceDE', 'w:autoSpaceDN', 'w:bidi', 'w:adjustRightInd', 'w:snapToGrid',
                   'w:spacing', 'w:ind', 'w:contextualSpacing', 'w:mirrorIndents', 'w:suppressOverlap', 'w:jc',
                   'w:textDirection', 'w:textAlignment', 'w:textboxTightWrap', 'w:outlineLvl', 'w:divId',
                   'w:cnfStyle', 'w:rPr', 'w:sectPr', 'w:pPrChange')


def _bottom_border(paragraph):
    """Trait sous le paragraphe (en-tête courant, comme dans les mémoires imprimés)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    ppr = paragraph._p.get_or_add_pPr()
    border = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    for key, value in (('w:val', 'single'), ('w:sz', '12'), ('w:space', '1'), ('w:color', '5A2D0C')):
        bottom.set(qn(key), value)
    border.append(bottom)
    successor = next((el for tag in _PPR_AFTER_PBDR if (el := ppr.find(qn(tag))) is not None), None)
    if successor is not None:
        successor.addprevious(border)
    else:
        ppr.append(border)


def _set_running_header(section, header):
    """En-tête courant « Chapitre I ............ Titre du chapitre », souligné. None : en-tête vide."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt
    section.header.is_linked_to_previous = False
    paragraph = section.header.paragraphs[0]
    for child in list(paragraph._p):
        if child.tag != qn('w:pPr'):
            paragraph._p.remove(child)
    if not header:
        return
    left, right = header
    fmt = paragraph.paragraph_format
    fmt.first_line_indent = Cm(0)
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.line_spacing = 1
    fmt.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fmt.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT)
    run = paragraph.add_run(f'{left}\t{right}' if left else f'\t{right}')
    run.font.size = Pt(11)
    _bottom_border(paragraph)


def start_docx_part(doc, number_format, restart=True, header=None, title_page=False):
    """Nouvelle section sur une nouvelle page.
    - `restart` : numérotation repartant de 1 (sinon elle continue) ;
    - `header` : (gauche, droite) de l'en-tête courant, ou None ;
    - `title_page` : la première page de la section est une page de titre, sans en-tête ni numéro."""
    from docx.enum.section import WD_SECTION
    from docx.shared import Cm
    section = doc.add_section(WD_SECTION.NEW_PAGE)
    section.left_margin = Cm(MARGINS_CM['left'])
    section.right_margin = Cm(MARGINS_CM['right'])
    section.top_margin = Cm(MARGINS_CM['top'])
    section.bottom_margin = Cm(MARGINS_CM['bottom'])
    section.header_distance = Cm(1.25)
    section.footer_distance = Cm(1.25)
    _set_page_numbering(section, number_format, restart)
    _add_page_number_footer(section)
    _set_running_header(section, header)
    section.different_first_page_header_footer = title_page
    if title_page:
        section.first_page_header.is_linked_to_previous = False
        section.first_page_footer.is_linked_to_previous = False
    return section


def add_docx_divider(doc, title):
    """Page de titre d'une grande partie (« Introduction », « Chapitre I »...), comme dans les mémoires imprimés."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt
    paragraph = doc.add_paragraph()
    fmt = paragraph.paragraph_format
    fmt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fmt.first_line_indent = Cm(0)
    fmt.space_before = Pt(220)
    fmt.space_after = Pt(0)
    fmt.line_spacing = 1.15
    run = paragraph.add_run(title)
    run.bold = True
    run.font.size = Pt(DIVIDER_SIZE)


def add_docx_body(doc, content):
    """Paragraphes d'un chapitre ; les éléments de liste sont alignés à gauche, sans retrait de première ligne."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm
    for text, is_item in body_paragraphs(content):
        paragraph = doc.add_paragraph(text)
        if is_item:
            fmt = paragraph.paragraph_format
            fmt.first_line_indent = Cm(-0.5)
            fmt.left_indent = Cm(FIRST_LINE_INDENT_CM)
            fmt.alignment = WD_ALIGN_PARAGRAPH.LEFT


def centered_docx_paragraph(doc, text, size_pt, bold=False, italic=False, space_after_pt=0):
    """Paragraphe centré sans retrait (page de garde, page de titre)."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt
    paragraph = doc.add_paragraph()
    fmt = paragraph.paragraph_format
    fmt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fmt.first_line_indent = Cm(0)
    fmt.line_spacing = 1.15
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(space_after_pt)
    if text:
        run = paragraph.add_run(text)
        run.font.size = Pt(size_pt)
        run.bold = bold
        run.italic = italic
    return paragraph


# ------------------------------------------------------------------ PDF (reportlab)

def pdf_styles():
    from reportlab.lib.colors import black
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm

    body = ParagraphStyle(
        'memoire-corps', fontName='Times-Roman', fontSize=BODY_SIZE, leading=BODY_SIZE * LINE_SPACING,
        alignment=TA_JUSTIFY, firstLineIndent=FIRST_LINE_INDENT_CM * cm,
        spaceBefore=PARAGRAPH_SPACING, spaceAfter=PARAGRAPH_SPACING, textColor=black,
    )
    item = ParagraphStyle('memoire-liste', parent=body, alignment=TA_LEFT, firstLineIndent=-0.5 * cm,
                          leftIndent=FIRST_LINE_INDENT_CM * cm)
    headings = {
        level: ParagraphStyle(
            f'memoire-titre-{level}', fontName='Times-Bold', fontSize=heading_size(level),
            leading=heading_size(level) * 1.3, textColor=black, keepWithNext=1,
            alignment=TA_CENTER if level == 1 else TA_LEFT,
            spaceBefore=0 if level == 1 else 12, spaceAfter=18 if level == 1 else PARAGRAPH_SPACING,
        )
        for level in (1, 2, 3)
    }
    return body, item, headings


def pdf_margins():
    from reportlab.lib.units import cm
    return {
        'leftMargin': MARGINS_CM['left'] * cm, 'rightMargin': MARGINS_CM['right'] * cm,
        'topMargin': MARGINS_CM['top'] * cm, 'bottomMargin': MARGINS_CM['bottom'] * cm,
    }


def to_roman(number):
    """4 → « iv » (chiffres romains minuscules des pages liminaires)."""
    result = ''
    for value, letters in ((1000, 'm'), (900, 'cm'), (500, 'd'), (400, 'cd'), (100, 'c'), (90, 'xc'), (50, 'l'),
                           (40, 'xl'), (10, 'x'), (9, 'ix'), (5, 'v'), (4, 'iv'), (1, 'i')):
        while number >= value:
            result += letters
            number -= value
    return result


def pdf_classes():
    """Gabarit PDF qui numérote chaque page selon la partie en cours (aucun numéro sur la page de garde)."""
    from reportlab.lib.units import cm
    from reportlab.platypus import Flowable, SimpleDocTemplate

    class NumberingStart(Flowable):
        """Marqueur invisible : à partir de cette page, numérotation `number_format` en repartant de 1."""

        def __init__(self, number_format):
            super().__init__()
            self.number_format = number_format
            self.width = self.height = 0

        def wrap(self, *args):
            return 0, 0

        def draw(self):
            self.canv._memoai_numbering = (self.number_format, self.canv.getPageNumber())

    class _Marker(Flowable):
        def __init__(self, value=None):
            super().__init__()
            self.value = value
            self.width = self.height = 0

        def wrap(self, *args):
            return 0, 0

    class HeaderStart(_Marker):
        """À partir de cette page : en-tête courant (gauche, droite), ou aucun si None."""

        def draw(self):
            self.canv._memoai_header = self.value

    class DividerMark(_Marker):
        """Cette page est une page de titre : ni en-tête ni numéro affiché."""

        def draw(self):
            self.canv._memoai_divider = self.canv.getPageNumber()

    class MemoirDocTemplate(SimpleDocTemplate):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Page physique → numéro affiché (« iii », « 4 ») ; conservé d'une passe de mise en page à l'autre
            # pour que le sommaire affiche les numéros définitifs.
            self.page_labels = {}

        def page_label(self):
            """Numéro affiché de la page en cours (« iv », « 12 ») ou None sur la page de garde."""
            numbering = getattr(self.canv, '_memoai_numbering', None)
            if not numbering:
                return None
            number_format, first_page = numbering
            number = self.canv.getPageNumber() - first_page + 1
            return to_roman(number) if number_format == FRONT_MATTER else str(number)

        def afterPage(self):
            label = self.page_label()
            if label is None:
                return  # page de garde
            canvas = self.canv
            self.page_labels[canvas.getPageNumber()] = label
            if getattr(canvas, '_memoai_divider', None) == canvas.getPageNumber():
                return  # page de titre d'une partie : ni en-tête ni numéro
            canvas.saveState()
            canvas.setFont('Times-Roman', 11)
            canvas.drawCentredString(self.leftMargin + self.width / 2, 1.3 * cm, label)
            header = getattr(canvas, '_memoai_header', None)
            if header:
                left, right = header
                y = self.pagesize[1] - 1.6 * cm
                canvas.setFont('Times-Roman', 10.5)
                if left:
                    canvas.drawString(self.leftMargin, y, left)
                canvas.drawRightString(self.leftMargin + self.width, y, right[:95])
                canvas.setStrokeColorRGB(0.35, 0.18, 0.05)
                canvas.setLineWidth(1.4)
                canvas.line(self.leftMargin, y - 5, self.leftMargin + self.width, y - 5)
            canvas.restoreState()

        def afterFlowable(self, flowable):
            # Titres de parties et de sections : entrées du sommaire, avec le numéro de page affiché.
            level = getattr(flowable, 'toc_level', None)
            if level:
                text = getattr(flowable, 'toc_text', None) or flowable.getPlainText()
                self.notify('TOCEntry', (level - 1, text, self.canv.getPageNumber()))

    return MemoirDocTemplate, NumberingStart, HeaderStart, DividerMark


# ------------------------------------------------------------------ Sommaire

TOC_TITLE = 'Sommaire'
TOC_DEPTH = 4  # parties / chapitres, sections, sous-sections et 4e niveau (I.1.2.1.)


def is_toc(chapter):
    """Partie « Sommaire » (ou « Table des matières ») ajoutée au plan : générée automatiquement."""
    title = (chapter.title or '').strip().lower()
    return title.startswith('sommaire') or title.startswith('table des mati')


def toc_entries(outline):
    """[(niveau, titre)] des parties et sections affichées dans le sommaire."""
    return [(level, chapter.title) for level, chapter in outline if level <= TOC_DEPTH and not is_toc(chapter)]


def add_docx_toc(doc, entries, page_break_before):
    """Sommaire Word : vraie table des matières (champ TOC) que Word met à jour avec les numéros de page.
    Les titres sont déjà écrits dans le champ : le sommaire reste lisible même avant la mise à jour."""
    from docx.enum.style import WD_STYLE_TYPE
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt

    title = doc.add_paragraph()
    fmt = title.paragraph_format
    fmt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fmt.first_line_indent = Cm(0)
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(18)
    fmt.page_break_before = page_break_before
    run = title.add_run(TOC_TITLE.upper())
    run.bold = True
    run.font.size = Pt(heading_size(1))

    # Styles des lignes du sommaire (utilisés aussi par Word lors de la mise à jour).
    for level in range(1, TOC_DEPTH + 1):
        name = f'TOC {level}'
        style = doc.styles[name] if name in [s.name for s in doc.styles] else doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = doc.styles['Normal']
        style.font.bold = level == 1
        sfmt = style.paragraph_format
        sfmt.first_line_indent = Cm(0)
        sfmt.left_indent = Cm(0.6 * (level - 1))
        sfmt.alignment = WD_ALIGN_PARAGRAPH.LEFT
        sfmt.space_before = Pt(3 if level == 1 else 0)
        sfmt.space_after = Pt(3 if level == 1 else 0)
        sfmt.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)

    def field_char(kind):
        r = OxmlElement('w:r')
        char = OxmlElement('w:fldChar')
        char.set(qn('w:fldCharType'), kind)
        r.append(char)
        return r

    for index, (level, text) in enumerate(entries):
        paragraph = doc.add_paragraph(style=f'TOC {level}')
        if index == 0:
            paragraph._p.append(field_char('begin'))
            instr_run = OxmlElement('w:r')
            instr = OxmlElement('w:instrText')
            instr.set(qn('xml:space'), 'preserve')
            instr.text = f' TOC \\o "1-{TOC_DEPTH}" \\h \\z \\u '
            instr_run.append(instr)
            paragraph._p.append(instr_run)
            paragraph._p.append(field_char('separate'))
        paragraph.add_run(text.replace('\n', ' : '))
        if index == len(entries) - 1:
            paragraph._p.append(field_char('end'))

    # Word propose de mettre à jour les champs à l'ouverture : les numéros de page s'affichent alors.
    settings = doc.settings.element
    if settings.find(qn('w:updateFields')) is None:
        update = OxmlElement('w:updateFields')
        update.set(qn('w:val'), 'true')
        settings.append(update)


def pdf_toc(doc):
    """Sommaire PDF : rempli automatiquement avec les numéros de page affichés (i, ii... puis 1, 2...)."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus.tableofcontents import TableOfContents
    toc = TableOfContents(formatter=lambda page: doc.page_labels.get(page, str(page)))
    toc.dotsMinLevel = 0
    toc.levelStyles = [
        ParagraphStyle('sommaire-1', fontName='Times-Bold', fontSize=BODY_SIZE, leading=BODY_SIZE * LINE_SPACING,
                       spaceBefore=3, firstLineIndent=0, leftIndent=0),
        ParagraphStyle('sommaire-2', fontName='Times-Roman', fontSize=BODY_SIZE, leading=BODY_SIZE * LINE_SPACING,
                       firstLineIndent=0, leftIndent=0.6 * cm),
        ParagraphStyle('sommaire-3', fontName='Times-Roman', fontSize=BODY_SIZE - 0.5, leading=BODY_SIZE * 1.4,
                       firstLineIndent=0, leftIndent=1.2 * cm),
        ParagraphStyle('sommaire-4', fontName='Times-Roman', fontSize=BODY_SIZE - 1, leading=BODY_SIZE * 1.35,
                       firstLineIndent=0, leftIndent=1.8 * cm),
    ]
    return toc


# ------------------------------------------------------------------ HTML (impression navigateur)

HTML_CSS = (
    f"@page{{size:A4;margin:{MARGINS_CM['top']}cm {MARGINS_CM['right']}cm {MARGINS_CM['bottom']}cm {MARGINS_CM['left']}cm;"
    "@bottom-center{content:counter(page)}}"
    f"body{{font-family:'{FONT}',Times,serif;font-size:{BODY_SIZE}pt;line-height:{LINE_SPACING};color:#000;"
    "max-width:16cm;margin:0 auto;padding:24px}"
    f"p{{text-align:justify;text-indent:{FIRST_LINE_INDENT_CM}cm;margin:{PARAGRAPH_SPACING}pt 0}}"
    f"p.item{{text-indent:-.5cm;padding-left:{FIRST_LINE_INDENT_CM}cm;text-align:left}}"
    f"h1,h2.chapitre{{font-size:{HEADING_SIZES[1]}pt;font-weight:bold;text-transform:uppercase;text-align:center;"
    "margin:0 0 18pt;break-before:page;page-break-before:always}"
    f"h3{{font-size:{HEADING_SIZES[2]}pt;font-weight:bold;margin:12pt 0 6pt;break-after:avoid}}"
    f"h4,h5,h6{{font-size:{HEADING_SIZES[3]}pt;font-weight:bold;margin:12pt 0 6pt;break-after:avoid}}"
    ".titre-page{text-align:center;text-indent:0}.meta{margin:2px 0;text-indent:0;text-align:center}"
    ".ref{padding-left:2em;text-indent:-2em;text-align:left}"
)
