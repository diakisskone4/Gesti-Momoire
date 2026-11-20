"""Page de garde des modèles dans les exports Word et PDF.

Reproduit, pour chacun des six styles (classique, moderne, élégant, thèse, minimaliste,
institutionnel), le rendu de l'aperçu HTML (`covers.render_cover_parts`) : mêmes informations,
même disposition, même couleur d'accent et mêmes ornements (cadres, bandeau, encadré du titre).

- `draw_pdf_cover(canvas, template, data)` dessine la page entière sur un canevas reportlab ;
- `add_docx_cover(doc, template, data)` remplit la première section d'un document python-docx.
"""
from html import escape

from .covers import STYLE_CSS

MM = 72 / 25.4  # points par millimètre


def style_of(template):
    return template.cover_style if template.cover_style in STYLE_CSS else 'classique'


def accent_of(template):
    color = str(template.accent_color or '')
    return color if len(color) == 7 and color.startswith('#') else '#0f766e'


def _title_label(style, data):
    return 'THÈSE' if style == 'these' or data.get('level') == 'DOCTORAT' else 'THÈME'


def _supervisors(data):
    return [(label, name) for label, name in (('Sous la direction de', data.get('supervisor')),
                                              ('Co-encadreur', data.get('co_supervisor'))) if name]


def _foot(data):
    return ' — '.join(filter(None, [data.get('city'),
                                    f"Année universitaire {data['academic_year']}" if data.get('academic_year') else '']))


# ====================================================================== PDF (reportlab)

# Marges de la page de garde (haut, droite, bas, gauche) en mm, comme l'aperçu HTML.
PDF_PADDING = {
    'classique': (20, 20, 18, 20), 'moderne': (20, 20, 18, 38), 'elegant': (26, 26, 22, 26),
    'these': (20, 20, 18, 20), 'minimaliste': (28, 26, 28, 26), 'institutionnel': (20, 20, 18, 20),
}


def draw_pdf_cover(canvas, template, data, page_width=595.2756, page_height=841.8898):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    style = style_of(template)
    accent = colors.HexColor(accent_of(template))
    gray = colors.HexColor('#4b5563')
    ink = colors.HexColor('#111827')
    sans = style in ('moderne', 'minimaliste')
    regular, bold, italic = (('Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique') if sans
                             else ('Times-Roman', 'Times-Bold', 'Times-Italic'))
    top, right, bottom, left = (v * MM for v in PDF_PADDING[style])
    x0, x1 = left, page_width - right
    width = x1 - x0
    head_align = TA_LEFT if style in ('moderne', 'minimaliste') else TA_CENTER
    body_align = TA_LEFT if style in ('moderne', 'minimaliste') else TA_CENTER

    def para(text, font, size, align=TA_CENTER, color=ink, leading=None, upper=False):
        text = text or ''
        return Paragraph(escape(text.upper() if upper else text),
                         ParagraphStyle('c', fontName=font, fontSize=size, leading=leading or size * 1.35,
                                        alignment=align, textColor=color))

    def put(p, x, y_top, w):
        """Dessine le paragraphe sous y_top ; renvoie sa hauteur."""
        _, h = p.wrap(w, page_height)
        p.drawOn(canvas, x, y_top - h)
        return h

    def height(p, w):
        return p.wrap(w, page_height)[1]

    canvas.saveState()

    # ---------------------------------------------------------------- ornements de page
    if style == 'moderne':
        canvas.setFillColor(accent)
        canvas.rect(0, 0, 22 * MM, page_height, stroke=0, fill=1)
        canvas.setFillAlpha(0.35)
        canvas.rect(22 * MM, 0, 3 * MM, page_height, stroke=0, fill=1)
        canvas.setFillAlpha(1)
    elif style == 'elegant':
        canvas.setStrokeColor(accent)
        for inset, line in ((9, 1.2), (10.4, 0.6)):
            canvas.setLineWidth(line)
            canvas.rect(inset * MM, inset * MM, page_width - 2 * inset * MM, page_height - 2 * inset * MM)
        canvas.setStrokeAlpha(0.5)
        canvas.setLineWidth(0.6)
        canvas.rect(13 * MM, 13 * MM, page_width - 26 * MM, page_height - 26 * MM)
        canvas.setStrokeAlpha(1)

    # ---------------------------------------------------------------- en-tête
    y = page_height - top
    head_color = gray if style == 'minimaliste' else ink
    if style == 'institutionnel':
        col = (width - 8 * MM) / 2
        left_lines = [para(data.get('ministry'), regular, 10),
                      para(data.get('university'), bold, 12, upper=True),
                      para(data.get('faculty'), regular, 11), para(data.get('department'), regular, 11)]
        right_lines = [para(data.get('country'), bold, 10.5, upper=True)]
        if data.get('motto'):
            right_lines.append(para(data['motto'], italic, 10))
        hl = yl = y
        for p in left_lines:
            yl -= put(p, x0, yl, col) + 2
        for p in right_lines:
            hl -= put(p, x0 + col + 8 * MM, hl, col) + 2
        y = min(yl, hl)
    else:
        lines = [para(data.get('country'), bold, 11.5, head_align, head_color, upper=True)]
        if data.get('motto'):
            lines.append(para(data['motto'], italic, 10, head_align, head_color))
        lines.append(para(data.get('ministry'), regular, 10, head_align, head_color))
        univ_size = 11 if style == 'minimaliste' else 13
        lines.append(para(data.get('university'), bold, univ_size, head_align, ink, upper=True))
        lines += [para(data.get('faculty'), regular, 11, head_align, head_color),
                  para(data.get('department'), regular, 11, head_align, head_color)]
        for i, p in enumerate(lines):
            if i == 3:
                y -= 6
            y -= put(p, x0, y, width) + 1.5

    # ---------------------------------------------------------------- mention du diplôme
    gap = {'minimaliste': 40, 'institutionnel': 14}.get(style, 12) * MM
    y -= gap
    if style == 'minimaliste':
        y -= put(para(data.get('diploma'), regular, 11, TA_LEFT, gray), x0, y, width)
    else:
        y -= put(para(data.get('diploma'), italic, 12, body_align), x0, y, width)
    diploma_bottom = y

    # ---------------------------------------------------------------- bas de page : pied, jury, personnes
    yb = bottom
    foot_color = accent if style == 'institutionnel' else (gray if style == 'minimaliste' else ink)
    foot_font = regular if style == 'minimaliste' else bold
    foot = para(_foot(data), foot_font, 11.5, body_align, foot_color)
    yb += height(foot, width)
    put(foot, x0, yb, width)
    yb += 10 * MM

    if data.get('jury'):
        jury_align = TA_LEFT if style in ('these', 'minimaliste', 'moderne') else TA_CENTER
        members = data['jury']
        if style == 'these':
            col = width / 2
            rows = [members[i:i + 2] for i in range(0, len(members), 2)]
            row_h = 11 * 1.45
            block = len(rows) * row_h
            yb += block
            for r, row in enumerate(rows):
                for c, name in enumerate(row):
                    put(para(name, regular, 11, TA_LEFT), x0 + c * col, yb - r * row_h, col - 4 * MM)
            label = para('Membres du jury', regular, 10, TA_LEFT, gray, upper=True)
            yb += height(label, width) + 3
            put(label, x0, yb, width)
            yb += 5 * MM
            canvas.setStrokeColor(colors.HexColor('#cbd5e1'))
            canvas.setLineWidth(0.8)
            canvas.line(x0, yb, x1, yb)
        else:
            names = [para(name, regular, 11, jury_align) for name in reversed(members)]
            for p in names:
                yb += height(p, width)
                put(p, x0, yb, width)
            label = para('Membres du jury', regular, 10, jury_align, gray, upper=True)
            yb += height(label, width) + 3
            put(label, x0, yb, width)
        yb += 8 * MM

    col = (width - 12 * MM) / 2
    left_block = [para('Présenté par', regular, 10, TA_LEFT, gray, upper=True), para(data.get('author'), bold, 12, TA_LEFT)]
    right_block = []
    for label, name in _supervisors(data):
        right_block += [para(label, regular, 10, TA_RIGHT, gray, upper=True), para(name, bold, 12, TA_RIGHT)]
    lh = sum(height(p, col) + 2 for p in left_block)
    rh = sum(height(p, col) + 2 for p in right_block)
    people_top = yb + max(lh, rh)
    yl = yr = people_top
    for p in left_block:
        yl -= put(p, x0, yl, col) + 2
    for p in right_block:
        yr -= put(p, x0 + col + 12 * MM, yr, col) + 2

    # ---------------------------------------------------------------- titre
    title_size = {'moderne': 22, 'minimaliste': 26, 'these': 19}.get(style, 20)
    title_font = regular if style == 'minimaliste' else bold
    title_color = accent if style in ('moderne', 'elegant') else ink
    pad_x = {'moderne': 7, 'these': 8, 'institutionnel': 6, 'classique': 4}.get(style, 0) * MM
    pad_y = {'classique': 8, 'these': 9, 'institutionnel': 8, 'moderne': 4}.get(style, 0) * MM
    inner_w = width - 2 * pad_x if style != 'moderne' else width - pad_x
    title_align = TA_LEFT if style in ('moderne', 'minimaliste') else TA_CENTER
    title = para(data.get('title'), title_font, title_size, title_align, title_color,
                 leading=title_size * 1.3, upper=style == 'elegant')
    th = height(title, inner_w)
    show_label = style != 'minimaliste'
    label_size = 12 if style == 'these' else 10
    label_h = label_size * 1.6 if show_label else 0
    ornament_h = 9 * MM if style == 'elegant' else 0
    box_h = pad_y * 2 + label_h + th + 2 * ornament_h

    if style == 'minimaliste':
        box_top = diploma_bottom - 6 * MM
    else:
        free_top, free_bottom = diploma_bottom - 8 * MM, people_top + 8 * MM
        box_top = free_bottom + (free_top - free_bottom + box_h) / 2
        box_top = min(box_top, free_top)
    box_bottom = box_top - box_h

    # cadre / encadré du titre
    if style == 'classique':
        canvas.setStrokeColor(ink)
        canvas.setLineWidth(2)
        canvas.line(x0, box_top, x1, box_top)
        canvas.line(x0, box_bottom, x1, box_bottom)
    elif style == 'moderne':
        canvas.setFillColor(accent)
        canvas.rect(x0, box_bottom, 5, box_h, stroke=0, fill=1)
    elif style == 'these':
        canvas.setFillColor(colors.HexColor('#f8fafc'))
        canvas.setStrokeColor(colors.HexColor('#cbd5e1'))
        canvas.setLineWidth(0.8)
        canvas.roundRect(x0, box_bottom, width, box_h, 2 * MM, stroke=1, fill=1)
    elif style == 'institutionnel':
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(2)
        canvas.rect(x0, box_bottom, width, box_h)
        canvas.setLineWidth(1)
        canvas.rect(x0 - 2 * MM, box_bottom - 2 * MM, width + 4 * MM, box_h + 4 * MM)

    y = box_top - pad_y
    text_x = x0 + (pad_x if style != 'moderne' else pad_x + 5)

    def ornament(y_center):
        canvas.setStrokeColor(accent)
        canvas.setFillColor(accent)
        canvas.setLineWidth(0.8)
        cx = page_width / 2 if style != 'moderne' else x0 + 20 * MM
        canvas.line(cx - 22 * MM, y_center, cx - 4 * MM, y_center)
        canvas.line(cx + 4 * MM, y_center, cx + 22 * MM, y_center)
        path = canvas.beginPath()
        path.moveTo(cx, y_center + 2.6 * MM)
        path.lineTo(cx + 2.6 * MM, y_center)
        path.lineTo(cx, y_center - 2.6 * MM)
        path.lineTo(cx - 2.6 * MM, y_center)
        path.close()
        canvas.drawPath(path, stroke=0, fill=1)

    if style == 'elegant':
        ornament(y - ornament_h / 2)
        y -= ornament_h
    if show_label:
        label_font = bold if style == 'institutionnel' else regular
        label_color = accent
        text = canvas.beginText()
        text.setFont(label_font, label_size)
        text.setFillColor(label_color)
        text.setCharSpace(6 if style == 'these' else 3)
        word = _title_label(style, data)
        word_w = canvas.stringWidth(word, label_font, label_size) + (6 if style == 'these' else 3) * (len(word) - 1)
        lx = text_x if title_align == TA_LEFT else x0 + (width - word_w) / 2
        text.setTextOrigin(lx, y - label_size)
        text.textLine(word)
        canvas.saveState()  # l'espacement des lettres ne doit pas s'appliquer au titre
        canvas.drawText(text)
        canvas.restoreState()
        canvas._charSpace = 0
        y -= label_h
    y -= put(title, text_x, y, inner_w)
    if style == 'elegant':
        ornament(y - ornament_h / 2)
    if style == 'minimaliste':
        canvas.setFillColor(accent)
        canvas.rect(x0, y - 8 * MM - 3, 30 * MM, 3, stroke=0, fill=1)

    canvas.restoreState()


def pdf_cover_flowable(template, data):
    """Flowable occupant toute la première page et dessinant la page de garde (coordonnées de la page)."""
    from reportlab.platypus import Flowable

    class CoverPage(Flowable):
        def wrap(self, avail_width, avail_height):
            self.avail = (avail_width, avail_height)
            return avail_width, avail_height

        def draw(self):
            doc = self.canv._doctemplate
            self.canv.saveState()
            self.canv.translate(-doc.leftMargin, -doc.bottomMargin)
            draw_pdf_cover(self.canv, template, data, *doc.pagesize)
            self.canv.restoreState()

    return CoverPage()


# ====================================================================== Word (python-docx)

DOCX_MARGINS_CM = {  # haut, droite, bas, gauche
    'classique': (2, 2, 1.8, 2), 'moderne': (2, 2, 1.8, 3.8), 'elegant': (2.6, 2.6, 2.2, 2.6),
    'these': (2, 2, 1.8, 2), 'minimaliste': (2.8, 2.6, 2.8, 2.6), 'institutionnel': (2, 2, 1.8, 2),
}

_PPR_ORDER = ('w:pStyle', 'w:keepNext', 'w:keepLines', 'w:pageBreakBefore', 'w:framePr', 'w:widowControl',
              'w:numPr', 'w:suppressLineNumbers', 'w:pBdr', 'w:shd', 'w:tabs', 'w:suppressAutoHyphens',
              'w:kinsoku', 'w:wordWrap', 'w:overflowPunct', 'w:topLinePunct', 'w:autoSpaceDE', 'w:autoSpaceDN',
              'w:bidi', 'w:adjustRightInd', 'w:snapToGrid', 'w:spacing', 'w:ind', 'w:contextualSpacing',
              'w:mirrorIndents', 'w:suppressOverlap', 'w:jc', 'w:textDirection', 'w:textAlignment',
              'w:textboxTightWrap', 'w:outlineLvl', 'w:divId', 'w:cnfStyle', 'w:rPr', 'w:sectPr', 'w:pPrChange')
_RPR_ORDER = ('w:rStyle', 'w:rFonts', 'w:b', 'w:bCs', 'w:i', 'w:iCs', 'w:caps', 'w:smallCaps', 'w:strike',
              'w:dstrike', 'w:outline', 'w:shadow', 'w:emboss', 'w:imprint', 'w:noProof', 'w:snapToGrid',
              'w:vanish', 'w:webHidden', 'w:color', 'w:spacing', 'w:w', 'w:kern', 'w:position', 'w:sz',
              'w:szCs', 'w:highlight', 'w:u', 'w:effect', 'w:bdr', 'w:shd', 'w:fitText', 'w:vertAlign',
              'w:rtl', 'w:cs', 'w:em', 'w:lang', 'w:eastAsianLayout', 'w:specVanish', 'w:oMath')
_SECT_ORDER = ('w:headerReference', 'w:footerReference', 'w:footnotePr', 'w:endnotePr', 'w:type', 'w:pgSz',
               'w:pgMar', 'w:paperSrc', 'w:pgBorders', 'w:lnNumType', 'w:pgNumType', 'w:cols', 'w:formProt',
               'w:vAlign', 'w:noEndnote', 'w:titlePg', 'w:textDirection', 'w:bidi', 'w:rtlGutter',
               'w:docGrid', 'w:printerSettings', 'w:sectPrChange')


def _insert_ordered(parent, element, order):
    """Insère `element` dans `parent` à la place imposée par le schéma Word (sinon « contenu illisible »)."""
    from docx.oxml.ns import qn
    tag = element.tag
    existing = parent.find(tag)
    if existing is not None:
        parent.remove(existing)
    names = [qn(n) for n in order]
    position = names.index(tag) if tag in names else len(names)
    for child in parent:
        if child.tag in names and names.index(child.tag) > position:
            child.addprevious(element)
            return element
    parent.append(element)
    return element


def _border(paragraph, color='111827', **sides):
    """Bordures de paragraphe : sides = {top|left|bottom|right: (style, épaisseur en 1/8 pt, espace pt)}."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    pbdr = OxmlElement('w:pBdr')
    for side in ('top', 'left', 'bottom', 'right'):
        if side in sides:
            val, size, space = sides[side]
            el = OxmlElement(f'w:{side}')
            for key, value in (('w:val', val), ('w:sz', str(size)), ('w:space', str(space)), ('w:color', color)):
                el.set(qn(key), value)
            pbdr.append(el)
    _insert_ordered(paragraph._p.get_or_add_pPr(), pbdr, _PPR_ORDER)


def _shade(paragraph, fill):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill)
    _insert_ordered(paragraph._p.get_or_add_pPr(), shd, _PPR_ORDER)


def _letter_spacing(run, points):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    el = OxmlElement('w:spacing')
    el.set(qn('w:val'), str(int(points * 20)))
    _insert_ordered(run._r.get_or_add_rPr(), el, _RPR_ORDER)


def _page_borders(section, color, **sides):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    borders = OxmlElement('w:pgBorders')
    borders.set(qn('w:offsetFrom'), 'page')
    for side in ('top', 'left', 'bottom', 'right'):
        if side in sides:
            val, size, space = sides[side]
            el = OxmlElement(f'w:{side}')
            for key, value in (('w:val', val), ('w:sz', str(size)), ('w:space', str(space)), ('w:color', color)):
                el.set(qn(key), value)
            borders.append(el)
    _insert_ordered(section._sectPr, borders, _SECT_ORDER)


def add_docx_cover(doc, template, data):
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt, RGBColor

    style = style_of(template)
    accent_hex = accent_of(template).lstrip('#').upper()
    accent = RGBColor.from_string(accent_hex)
    gray = RGBColor.from_string('4B5563')
    ink = RGBColor.from_string('111827')
    font_name = {'moderne': 'Segoe UI', 'minimaliste': 'Arial'}.get(style, 'Times New Roman')
    left_aligned = style in ('moderne', 'minimaliste')
    head_align = WD_ALIGN_PARAGRAPH.LEFT if left_aligned else WD_ALIGN_PARAGRAPH.CENTER

    section = doc.sections[0]
    top, right, bottom, left = DOCX_MARGINS_CM[style]
    section.top_margin, section.right_margin = Cm(top), Cm(right)
    section.bottom_margin, section.left_margin = Cm(bottom), Cm(left)
    if style == 'elegant':
        _page_borders(section, accent_hex, **{s: ('double', 18, 24) for s in ('top', 'left', 'bottom', 'right')})
    elif style == 'moderne':
        _page_borders(section, accent_hex, left=('single', 96, 0))

    # Mise en page compacte si le titre ou le jury sont longs (la page de garde tient sur une page).
    long_content = len(data.get('title') or '') > 110 or len(data.get('jury') or []) > 3
    scale = 0.6 if long_content else 1.0

    def paragraph(text='', size=12, bold=False, italic=False, color=None, align=None, before=0, after=0,
                  upper=False, spacing=None, container=None, small_caps=False):
        p = (container or doc).add_paragraph()
        pf = p.paragraph_format
        pf.alignment = align if align is not None else head_align
        pf.first_line_indent = Cm(0)
        pf.left_indent = Cm(0)
        pf.space_before = Pt(before)
        pf.space_after = Pt(after)
        pf.line_spacing = 1.15
        pf.keep_with_next = False
        if text:
            run = p.add_run(text.upper() if upper else text)
            run.font.name = font_name
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.italic = italic
            run.font.small_caps = small_caps
            run.font.color.rgb = color or ink
            if spacing:
                _letter_spacing(run, spacing)
        return p

    def borderless_table(cols):
        table = doc.add_table(rows=1, cols=cols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        tbl_pr = table._tbl.tblPr
        borders = OxmlElement('w:tblBorders')
        for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            el = OxmlElement(f'w:{side}')
            el.set(qn('w:val'), 'nil')
            borders.append(el)
        tbl_pr.append(borders)
        for cell in table.rows[0].cells:
            cell.paragraphs[0]._p.getparent().remove(cell.paragraphs[0]._p)
        return table

    # ---------------------------------------------------------------- en-tête
    if style == 'institutionnel':
        table = borderless_table(2)
        left_cell, right_cell = table.rows[0].cells
        center = WD_ALIGN_PARAGRAPH.CENTER
        paragraph(data.get('ministry'), 10, align=center, container=left_cell)
        paragraph(data.get('university'), 12, bold=True, align=center, upper=True, before=4, container=left_cell)
        paragraph(data.get('faculty'), 11, align=center, container=left_cell)
        paragraph(data.get('department'), 11, align=center, container=left_cell)
        paragraph(data.get('country'), 10.5, bold=True, align=center, upper=True, container=right_cell)
        if data.get('motto'):
            paragraph(data['motto'], 10, italic=True, align=center, container=right_cell)
    else:
        head_color = gray if style == 'minimaliste' else ink
        paragraph(data.get('country'), 11.5, bold=True, upper=True, color=head_color)
        if data.get('motto'):
            paragraph(data['motto'], 10, italic=True, color=head_color)
        paragraph(data.get('ministry'), 10, color=head_color, before=3)
        paragraph(data.get('university'), 11 if style == 'minimaliste' else 13, bold=True, upper=True, before=7)
        paragraph(data.get('faculty'), 11, color=head_color)
        paragraph(data.get('department'), 11, color=head_color)

    # ---------------------------------------------------------------- diplôme
    if style == 'minimaliste':
        paragraph(data.get('diploma'), 11, color=gray, before=80 * scale)
    else:
        paragraph(data.get('diploma'), 12, italic=True, before=(46 if style == 'institutionnel' else 40) * scale,
                  align=head_align)

    # ---------------------------------------------------------------- titre
    title_align = WD_ALIGN_PARAGRAPH.LEFT if left_aligned else WD_ALIGN_PARAGRAPH.CENTER
    title_size = {'moderne': 22, 'minimaliste': 26, 'these': 19}.get(style, 20)
    if len(data.get('title') or '') > 110:
        title_size = round(title_size * 0.8)  # titre long : la page de garde reste sur une page
    before_title = (18 if style == 'minimaliste' else 96) * scale
    block = []
    if style == 'elegant':
        block.append(paragraph('❦', 16, color=accent, align=title_align, before=before_title, after=6))
        before_title = 0
    if style != 'minimaliste':
        label = paragraph(_title_label(style, data), 12 if style == 'these' else 10,
                          bold=style == 'institutionnel', color=accent, align=title_align,
                          before=before_title, after=4, spacing=6 if style == 'these' else 3)
        block.append(label)
        before_title = 0
    title = paragraph(data.get('title'), title_size, bold=style != 'minimaliste',
                      color=accent if style in ('moderne', 'elegant') else ink, align=title_align,
                      before=before_title, small_caps=style == 'elegant')
    title.paragraph_format.line_spacing = 1.2
    block.append(title)
    if style == 'elegant':
        block.append(paragraph('❦', 16, color=accent, align=title_align, before=6))
    if style == 'minimaliste':
        bar = paragraph('', 6, align=WD_ALIGN_PARAGRAPH.LEFT, before=14)
        bar.paragraph_format.right_indent = Cm(21 - left - right - 3)
        _border(bar, accent_hex, bottom=('single', 24, 1))

    box = {
        'classique': dict(top=('single', 16, 10), bottom=('single', 16, 10)),
        'moderne': dict(left=('single', 36, 10)),
        'these': dict(top=('single', 6, 12), bottom=('single', 6, 12), left=('single', 6, 12), right=('single', 6, 12)),
        'institutionnel': dict(top=('double', 12, 10), bottom=('double', 12, 10), left=('double', 12, 10),
                               right=('double', 12, 10)),
    }.get(style)
    if box:
        color = {'classique': '111827', 'these': 'CBD5E1'}.get(style, accent_hex)
        for p in block:
            _border(p, color, **box)
            if style == 'these':
                _shade(p, 'F8FAFC')

    # ---------------------------------------------------------------- personnes
    paragraph('', 6, before=(104 if style != 'minimaliste' else 96) * scale)
    table = borderless_table(2)
    left_cell, right_cell = table.rows[0].cells
    lalign, ralign = WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.RIGHT
    paragraph('Présenté par', 10, color=gray, align=lalign, upper=True, spacing=1, container=left_cell)
    paragraph(data.get('author'), 12, bold=True, align=lalign, container=left_cell)
    for label, name in _supervisors(data):
        paragraph(label, 10, color=gray, align=ralign, upper=True, spacing=1, container=right_cell)
        paragraph(name, 12, bold=True, align=ralign, after=4, container=right_cell)
    if not right_cell.paragraphs:
        paragraph('', 10, container=right_cell)

    # ---------------------------------------------------------------- jury et pied
    if data.get('jury'):
        jury_align = WD_ALIGN_PARAGRAPH.LEFT if style in ('these', 'minimaliste', 'moderne') else WD_ALIGN_PARAGRAPH.CENTER
        label = paragraph('Membres du jury', 10, color=gray, align=jury_align, upper=True, spacing=1, before=18 * scale)
        if style == 'these':
            _border(label, 'CBD5E1', top=('single', 6, 8))
        for name in data['jury']:
            paragraph(name, 11, align=jury_align)
    foot_color = accent if style == 'institutionnel' else (gray if style == 'minimaliste' else ink)
    paragraph(_foot(data), 11.5, bold=style != 'minimaliste', color=foot_color, before=48 * scale,
              align=WD_ALIGN_PARAGRAPH.LEFT if left_aligned else WD_ALIGN_PARAGRAPH.CENTER)
