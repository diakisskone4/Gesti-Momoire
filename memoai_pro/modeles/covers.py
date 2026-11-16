"""Pages de garde des modèles de mémoire.

`cover_data()` rassemble les informations (projet réel ou exemple), `render_cover_html()`
produit une page A4 autonome dans l'un des six styles. Le même rendu sert à l'aperçu
dans le catalogue et à l'export HTML ; `cover_lines()` alimente les exports DOCX/PDF.
"""
from html import escape

LEVEL_DIPLOMAS = {'LICENCE': 'Licence', 'MASTER': 'Master', 'DOCTORAT': 'Doctorat'}
MALI = {'country': 'République du Mali', 'motto': 'Un Peuple – Un But – Une Foi'}

SAMPLE = {
    'country': MALI['country'],
    'motto': MALI['motto'],
    'ministry': "Ministère de l'Enseignement Supérieur et de la Recherche Scientifique",
    'university': 'Université des Sciences Sociales et de Gestion de Bamako',
    'faculty': 'Faculté des Sciences Économiques et de Gestion',
    'department': 'Département Gestion',
    'field': 'Finance et Comptabilité',
    'title': "Impact du mobile money sur l'inclusion financière des ménages ruraux au Mali",
    'author': 'Aminata TRAORÉ',
    'supervisor': 'Pr. Moussa DIARRA',
    'co_supervisor': 'Dr. Fatoumata KONÉ',
    'jury': ['Pr. Oumar SANGARÉ (Président)', 'Dr. Ibrahim COULIBALY (Examinateur)'],
    'academic_year': '2025-2026',
    'city': 'Bamako',
}


def diploma_line(level, field):
    diploma = LEVEL_DIPLOMAS.get(level or '', '')
    if level == 'DOCTORAT':
        base = 'Thèse présentée et soutenue publiquement pour l\'obtention du grade de Docteur'
    elif diploma:
        base = f"Mémoire de fin de cycle pour l'obtention du diplôme de {diploma}"
    else:
        base = "Mémoire de fin d'études"
    return f'{base} en {field}' if field else base


def cover_data(template, project=None, user=None):
    """Données de la page de garde : celles du mémoire si fourni, sinon un exemple réaliste."""
    if project is None:
        data = dict(SAMPLE)
        data['level'] = template.level or 'MASTER'
        data['diploma'] = diploma_line(data['level'], data['field'])
        return data

    owner = project.user
    country = (project.country or '').strip()
    is_mali = not country or country.lower() == 'mali'
    person = lambda u: ' '.join(filter(None, [u.academic_title, u.full_name])) if u else ''
    data = {
        'country': MALI['country'] if is_mali else country,
        'motto': MALI['motto'] if is_mali else '',
        'ministry': "Ministère de l'Enseignement Supérieur et de la Recherche Scientifique",
        'university': project.university or owner.university or '',
        'faculty': project.faculty or owner.faculty or '',
        'department': project.department or owner.department or '',
        'field': project.field_of_study or '',
        'title': project.title,
        'author': owner.full_name,
        'supervisor': person(project.supervisor),
        'co_supervisor': person(project.co_supervisor),
        'jury': [person(u) for u in project.jury.all()],
        'academic_year': project.academic_year or '',
        'city': project.city or '',
        'level': project.level,
    }
    data['diploma'] = diploma_line(project.level, data['field'])
    return data


def cover_lines(data):
    """Version texte de la page de garde (exports DOCX / PDF) : [(texte, rôle), ...]."""
    lines = [(data['country'], 'header'), (data.get('motto', ''), 'motto'), (data['ministry'], 'small'),
             (data['university'], 'header'), (data['faculty'], 'small'), (data['department'], 'small'),
             ('', 'space'), (data['diploma'], 'diploma'), ('', 'space'), (data['title'], 'title'), ('', 'space'),
             (f"Présenté par : {data['author']}", 'person')]
    if data.get('supervisor'):
        lines.append((f"Sous la direction de : {data['supervisor']}", 'person'))
    if data.get('co_supervisor'):
        lines.append((f"Co-encadrement : {data['co_supervisor']}", 'person'))
    if data.get('jury'):
        lines.append(('Membres du jury : ' + ' ; '.join(data['jury']), 'small'))
    footer = ' — '.join(filter(None, [data.get('city'), f"Année universitaire {data['academic_year']}" if data.get('academic_year') else '']))
    lines += [('', 'space'), (footer, 'footer')]
    return [(text, role) for text, role in lines if text or role == 'space']


DOC_CSS = "html,body{margin:0;padding:0;background:#e5e7eb}@media print{html,body{background:#fff}}"

BASE_CSS = """
.page,.page *{box-sizing:border-box}
.page{width:210mm;height:297mm;margin:0 auto;background:#fff;color:#111827;position:relative;overflow:hidden;
  font-family:'Times New Roman',Georgia,serif;display:flex;flex-direction:column;padding:20mm 20mm 18mm}
.head{text-align:center;font-size:11.5pt;line-height:1.45}
.head .country{font-weight:700;text-transform:uppercase;letter-spacing:.5px}
.head .motto{font-style:italic;font-size:10pt}
.head .ministry{font-size:10pt;margin-top:6px}
.head .univ{font-weight:700;font-size:13pt;margin-top:10px;text-transform:uppercase}
.head .sub{font-size:11pt}
.diploma{text-align:center;font-size:12pt;font-style:italic;margin-top:12mm}
.title-box{margin:auto 0;padding-top:10mm;padding-bottom:10mm;text-align:center}
.title-box .label{font-size:10pt;letter-spacing:3px;text-transform:uppercase;color:var(--accent)}
.title-box h1{font-size:20pt;line-height:1.3;margin:6px 0 0;color:#111827}
.people{display:flex;justify-content:space-between;gap:12mm;font-size:12pt;line-height:1.6}
.people .col{flex:1}.people .col.right{text-align:right}
.people .role{font-size:10pt;text-transform:uppercase;letter-spacing:1px;color:#4b5563}
.people strong{display:block}
.jury{margin-top:8mm;font-size:11pt;text-align:center}
.jury .role{font-size:10pt;text-transform:uppercase;letter-spacing:1px;color:#4b5563}
.foot{text-align:center;font-size:11.5pt;margin-top:10mm;font-weight:700}
.watermark{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;
  font:700 64pt Arial,sans-serif;color:rgba(15,23,42,.07);transform:rotate(-30deg);letter-spacing:8px}
@media print{.page{margin:0}}
"""

STYLE_CSS = {
    'classique': """
.page{border:0}
.title-box{border-top:2px solid #111827;border-bottom:2px solid #111827;padding:8mm 4mm}
""",
    'moderne': """
.page{padding-left:38mm;font-family:'Segoe UI',Arial,sans-serif}
.page:before{content:'';position:absolute;left:0;top:0;bottom:0;width:22mm;background:var(--accent)}
.page:after{content:'';position:absolute;left:22mm;top:0;bottom:0;width:3mm;background:var(--accent);opacity:.35}
.head{text-align:left}.diploma{text-align:left}
.title-box{text-align:left;border-left:5px solid var(--accent);padding:4mm 0 4mm 7mm}
.title-box h1{font-size:22pt;font-weight:800;color:var(--accent)}
.foot{text-align:left}
""",
    'elegant': """
.page{padding:26mm 26mm 22mm}
.page:before{content:'';position:absolute;inset:9mm;border:3px double var(--accent)}
.page:after{content:'';position:absolute;inset:13mm;border:1px solid var(--accent);opacity:.5}
.title-box h1{font-variant:small-caps;color:var(--accent)}
.title-box:before,.title-box:after{content:'❦';display:block;color:var(--accent);font-size:16pt;margin:3mm 0}
""",
    'these': """
.title-box{background:#f8fafc;border:1px solid #cbd5e1;padding:9mm 8mm;border-radius:2mm}
.title-box .label{font-size:12pt;letter-spacing:6px}
.title-box h1{font-size:19pt}
.jury{border-top:1px solid #cbd5e1;padding-top:5mm;text-align:left}
.jury ul{margin:2mm 0 0;padding:0;list-style:none;columns:2;font-size:11pt}
""",
    'minimaliste': """
.page{font-family:'Helvetica Neue',Arial,sans-serif;padding:28mm 26mm}
.head{text-align:left;font-size:10pt;color:#4b5563}.head .univ{font-size:11pt;color:#111827}
.diploma{text-align:left;font-style:normal;color:#4b5563;font-size:11pt;margin-top:40mm}
.title-box{text-align:left;margin:6mm 0 auto}
.title-box .label{display:none}
.title-box h1{font-size:26pt;font-weight:300;line-height:1.2}
.title-box:after{content:'';display:block;width:30mm;height:3px;background:var(--accent);margin-top:8mm}
.foot{text-align:left;font-weight:400;color:#4b5563}
.jury{text-align:left}
""",
    'institutionnel': """
.head{display:grid;grid-template-columns:1fr 1fr;gap:8mm;text-align:center}
.head .left .country,.head .right .country{font-size:10.5pt}
.diploma{margin-top:14mm}
.title-box{border:2px solid var(--accent);padding:8mm 6mm;outline:1px solid var(--accent);outline-offset:2mm}
.title-box .label{color:var(--accent);font-weight:700}
.foot{color:var(--accent)}
""",
}


def _e(value):
    return escape(value or '')


def render_cover_parts(template, data, watermark=False):
    """(css, html) de la page de garde, pour l'intégrer dans un autre document."""
    style = template.cover_style if template.cover_style in STYLE_CSS else 'classique'
    accent = template.accent_color if str(template.accent_color).startswith('#') else '#0f766e'
    is_thesis = style == 'these' or data.get('level') == 'DOCTORAT'

    if style == 'institutionnel':
        head = f"""
<div class="head">
  <div class="left">
    <div class="ministry">{_e(data['ministry'])}</div>
    <div class="univ">{_e(data['university'])}</div>
    <div class="sub">{_e(data['faculty'])}</div><div class="sub">{_e(data['department'])}</div>
  </div>
  <div class="right">
    <div class="country">{_e(data['country'])}</div>
    <div class="motto">{_e(data.get('motto'))}</div>
  </div>
</div>"""
    else:
        head = f"""
<div class="head">
  <div class="country">{_e(data['country'])}</div>
  {f'<div class="motto">{_e(data["motto"])}</div>' if data.get('motto') else ''}
  <div class="ministry">{_e(data['ministry'])}</div>
  <div class="univ">{_e(data['university'])}</div>
  <div class="sub">{_e(data['faculty'])}</div>
  <div class="sub">{_e(data['department'])}</div>
</div>"""

    supervisors = ''.join(
        f'<div class="role">{label}</div><strong>{_e(name)}</strong>'
        for label, name in (('Sous la direction de', data.get('supervisor')), ('Co-encadreur', data.get('co_supervisor')))
        if name
    )
    jury = ''
    if data.get('jury'):
        items = ''.join(f'<li>{_e(m)}</li>' for m in data['jury'])
        jury = f'<div class="jury"><div class="role">Membres du jury</div><ul style="list-style:none;padding:0;margin:2mm 0 0">{items}</ul></div>'

    foot = ' — '.join(filter(None, [_e(data.get('city')),
                                    f"Année universitaire {_e(data['academic_year'])}" if data.get('academic_year') else '']))

    css = f'.page{{--accent:{accent}}}' + BASE_CSS + STYLE_CSS[style]
    page = f"""<div class="page">
{head}
<div class="diploma">{_e(data['diploma'])}</div>
<div class="title-box"><div class="label">{'Thèse' if is_thesis else 'Thème'}</div><h1>{_e(data['title'])}</h1></div>
<div class="people">
  <div class="col"><div class="role">Présenté par</div><strong>{_e(data['author'])}</strong></div>
  <div class="col right">{supervisors}</div>
</div>
{jury}
<div class="foot">{foot}</div>
{'<div class="watermark">APERÇU</div>' if watermark else ''}
</div>"""
    return css, page


def render_cover_html(template, data, watermark=False):
    """Page de garde autonome (document HTML complet)."""
    css, page = render_cover_parts(template, data, watermark)
    return (f'<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
            f'<title>Page de garde — {_e(data["title"])}</title><style>{DOC_CSS}{css}</style></head>'
            f'<body>{page}</body></html>')
