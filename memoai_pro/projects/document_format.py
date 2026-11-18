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

    # Numéro de page centré en bas, absent de la première page (page de garde).
    for section in doc.sections:
        section.different_first_page_header_footer = True
        paragraph = section.footer.paragraphs[0]
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


def draw_pdf_page_number(canvas, doc):
    """Numéro de page centré sous le bloc de texte (pages suivant la page de garde)."""
    from reportlab.lib.units import cm
    canvas.saveState()
    canvas.setFont('Times-Roman', 11)
    canvas.drawCentredString(doc.leftMargin + doc.width / 2, 1.3 * cm, str(doc.page))
    canvas.restoreState()


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
