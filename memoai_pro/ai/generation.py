"""Génération du plan et du contenu d'un mémoire par l'IA.

Réservée aux mémoires dont le modèle (page de garde + plan type) a été acheté.
Le texte écrit par l'étudiant n'est jamais écrasé : seuls les chapitres vides ou
contenant uniquement un conseil de modèle (« [Conseil du modèle : ...] ») sont remplacés.
"""
import re

from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError

from projects.models import Chapter
from .services import AIService

PLACEHOLDER = re.compile(r'^\s*(\[(Conseil du modèle|Sous-parties prévues)[^\]]*\]\s*)*$', re.DOTALL)
NON_GENERATED_TYPES = {'preliminary', 'back'}  # dédicace, remerciements, résumé, bibliographie, annexes


class PaymentRequired(APIException):
    status_code = 402
    default_detail = 'Achetez un modèle de mémoire pour utiliser la génération par IA.'
    default_code = 'template_required'


def is_placeholder(content):
    return not content or bool(PLACEHOLDER.match(content))


def guidance_of(content):
    """Consignes contenues dans un chapitre de modèle, pour les transmettre à l'IA."""
    return ' '.join(m.group(1).strip() for m in re.finditer(r'\[(?:Conseil du modèle|Sous-parties prévues)\s*:\s*([^\]]*)\]', content or ''))


def _price_label():
    """Prix d'un modèle tel qu'affiché : « 5 000 FCFA »."""
    from decimal import Decimal
    from django.conf import settings
    return f"{int(Decimal(settings.MODELE_PRICE)):,} FCFA".replace(',', ' ')


def require_paid_template(project):
    template = project.template
    if template is None or not template.is_owned_by(project.user):
        raise PaymentRequired(
            "La génération du plan et du contenu par l'IA est réservée aux mémoires qui utilisent un modèle "
            f"acheté. Choisissez un modèle ({_price_label()}) dans « Modèles de mémoire » puis appliquez-le à ce mémoire."
        )
    return template


def user_written_chapters(project):
    return [c for c in project.chapters.all() if not is_placeholder(c.content)]


def project_context(project):
    parts = [f'Titre : {project.title}', f'Niveau : {project.get_level_display()}']
    for label, value in (('Thème / problématique', project.theme), ("Domaine d'étude", project.field_of_study),
                         ('Option', project.option), ('Université', project.university),
                         ('Pays', project.country), ('Ville', project.city)):
        if value:
            parts.append(f'{label} : {value}')
    return ' ; '.join(parts)


def template_guide(template):
    lines = []
    for entry in template.structure:
        if entry.get('type') in NON_GENERATED_TYPES:
            continue
        sections = ', '.join(s['title'] for s in entry.get('sections', []))
        lines.append(f"- {entry['title']}" + (f" (sections : {sections})" if sections else ''))
    return '\n'.join(lines)


def check_plan_allowed(project):
    require_paid_template(project)
    written = user_written_chapters(project)
    if written:
        raise ValidationError({'error': (
            f"Votre mémoire contient déjà du texte rédigé ({len(written)} chapitre(s) ou section(s)). "
            "Pour ne pas l'écraser, le plan n'est pas régénéré : utilisez « Rédiger avec l'IA » "
            "sur les chapitres encore vides."
        )})


def rebuild_plan(project, plan_data):
    """Remplace les chapitres sans contenu par : pages liminaires du modèle + plan IA + fin du modèle."""
    template = project.template
    entries = template.structure if template else []
    preliminaries = [e for e in entries if e.get('type') == 'preliminary']
    back = [e for e in entries if e.get('type') == 'back']

    def advice(text):
        return f'[Conseil du modèle : {text}]\n\n' if text else ''

    with transaction.atomic():
        project.chapters.all().delete()  # tous sans contenu rédigé (vérifié avant l'appel à l'IA)
        order = 0

        def create(title, kind, content='', parent=None, position=None):
            return Chapter.objects.create(project=project, parent=parent, title=title[:255], type=kind,
                                          content=content, order=position)

        for entry in preliminaries:
            order += 1
            create(entry['title'], 'preliminary', advice(entry.get('guidance')), position=order)
        for index, chapter_data in enumerate(plan_data.get('chapters', []), start=1):
            order += 1
            chapter = create(chapter_data.get('title') or f'Chapitre {index}', 'chapter', position=order)
            for s_index, section in enumerate(chapter_data.get('sections', []), start=1):
                subsections = [s for s in section.get('subsections', []) if s]
                content = f"[Sous-parties prévues : {' ; '.join(subsections)}]\n\n" if subsections else ''
                create(section.get('title') or f'Section {s_index}', 'section', content, chapter, s_index)
        for entry in back:
            order += 1
            create(entry['title'], 'back', advice(entry.get('guidance')), position=order)

        project.status = 'IN_PROGRESS'
        project.save(update_fields=['status', 'updated_at'])


def generable_chapters(project):
    """Chapitres de premier niveau que l'IA peut rédiger (hors pages liminaires et bibliographie)."""
    return [c for c in project.chapters.filter(parent=None).order_by('order', 'id')
            if c.type not in NON_GENERATED_TYPES]


def needs_content(chapter):
    return is_placeholder(chapter.content) or any(is_placeholder(s.content) for s in chapter.children.all())


def write_chapter_content(project, chapter):
    """Rédige l'introduction et les sections encore vides d'un chapitre. Renvoie le nombre de blocs écrits."""
    require_paid_template(project)
    if chapter.parent_id is not None:
        raise ValidationError({'error': 'Lancez la rédaction depuis le chapitre parent.'})
    if chapter.type in NON_GENERATED_TYPES:
        raise ValidationError({'error': 'Cette page (dédicace, remerciements, résumé, bibliographie, annexes) '
                                        'doit être rédigée par vous.'})
    sections = list(chapter.children.order_by('order', 'id'))
    if not needs_content(chapter):
        raise ValidationError({'error': 'Ce chapitre est déjà entièrement rédigé.'})

    pages = project.desired_pages or 40
    blocks = max(sum(max(c.children.count(), 1) for c in generable_chapters(project)), 1)
    words = int(min(700, max(250, pages * 300 / blocks)))  # environ 300 mots par page

    result = AIService.write_chapter(
        project_context(project), chapter.title, guidance_of(chapter.content),
        [(s.title, guidance_of(s.content)) for s in sections], words, project.language or 'fr',
    )

    written = 0
    with transaction.atomic():
        if is_placeholder(chapter.content) and result['intro']:
            chapter.content = result['intro']
            chapter.version += 1
            chapter.save(update_fields=['content', 'version', 'updated_at'])
            written += 1
        for number, section in enumerate(sections, start=1):
            text = result['sections'].get(number)
            if text and is_placeholder(section.content):
                section.content = text
                section.version += 1
                section.save(update_fields=['content', 'version', 'updated_at'])
                written += 1
    if not written:
        raise ValidationError({'error': "L'IA n'a produit aucun contenu exploitable. Réessayez."})
    return written
