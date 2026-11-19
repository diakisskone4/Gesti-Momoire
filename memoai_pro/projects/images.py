"""Images des mémoires (figures) : envoi, lecture, suppression.

POST   /projects/images/          {project, data: « data:image/png;base64,... »}  → {id, width, height, marker}
GET    /projects/images/<id>/     le fichier image (auteur, encadreurs, jury, administrateur)
DELETE /projects/images/<id>/     (auteur uniquement)

Dans le texte d'un chapitre, une figure s'insère sur sa propre ligne : [Figure:ID | légende].
"""
import base64
import binascii
import re
from io import BytesIO

from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import get_owned_project, visible_projects
from .models import ProjectImage

MAX_UPLOAD_BYTES = 8 * 1024 * 1024      # avant redimensionnement
MAX_SIDE = 1600                          # pixels, côté le plus long
MAX_IMAGES_PER_PROJECT = 150
MAX_PIXELS = 40_000_000
ALLOWED_FORMATS = {'PNG', 'JPEG', 'WEBP', 'GIF', 'MPO'}  # MPO : certaines photos d'appareils
_DATA_URL = re.compile(r'^data:image/[a-zA-Z0-9.+-]+;base64,(?P<data>.+)$', re.DOTALL)


def figure_marker(image_id, caption=''):
    return f'[Figure:{image_id} | {caption.strip()}]' if caption.strip() else f'[Figure:{image_id}]'


def normalize_image(raw):
    """Vérifie que les octets sont une vraie image, la réduit à 1600 px et la convertit
    en PNG (dessins, transparence) ou JPEG (photos). Renvoie (octets, type, largeur, hauteur)."""
    import warnings

    from PIL import Image, ImageOps, UnidentifiedImageError
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS  # « bombes de décompression » : image minuscule qui occupe des Go en mémoire
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            image = Image.open(BytesIO(raw))
            if image.format not in ALLOWED_FORMATS:
                raise ValidationError({'error': 'Format non pris en charge (PNG, JPEG, WEBP ou GIF).'})
            image.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError({'error': 'Image trop grande (40 mégapixels maximum).'})
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise ValidationError({'error': "Ce fichier n'est pas une image valide (PNG, JPEG, WEBP ou GIF)."})
    source_format = (image.format or '').upper()  # perdu par exif_transpose
    image = ImageOps.exif_transpose(image)  # photos de téléphone : orientation correcte
    if image.mode == 'P':
        image = image.convert('RGBA')
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    has_alpha = image.mode in ('RGBA', 'LA')
    out = BytesIO()
    if has_alpha or (source_format == 'PNG' and len(raw) < 1_500_000):
        image.save(out, format='PNG', optimize=True)
        content_type = 'image/png'
    else:
        image.convert('RGB').save(out, format='JPEG', quality=85, optimize=True)
        content_type = 'image/jpeg'
    return out.getvalue(), content_type, image.width, image.height


class ProjectImageUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'upload'

    def post(self, request):
        project = get_owned_project(request.user, request.data.get('project'))
        match = _DATA_URL.match(str(request.data.get('data') or ''))
        if not match:
            raise ValidationError({'error': 'Image manquante ou format non reconnu.'})
        try:
            raw = base64.b64decode(match.group('data'), validate=False)
        except (binascii.Error, ValueError):
            raise ValidationError({'error': 'Image illisible.'})
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValidationError({'error': 'Image trop lourde (8 Mo maximum).'})
        if project.images.count() >= MAX_IMAGES_PER_PROJECT:
            raise ValidationError({'error': f'Limite de {MAX_IMAGES_PER_PROJECT} images atteinte pour ce mémoire.'})
        data, content_type, width, height = normalize_image(raw)
        image = ProjectImage.objects.create(
            project=project, uploaded_by=request.user, data=data, content_type=content_type,
            width=width, height=height, size=len(data),
        )
        caption = str(request.data.get('caption') or '')[:300]
        return Response({'id': image.id, 'width': width, 'height': height, 'size': len(data),
                         'marker': figure_marker(image.id, caption)}, status=status.HTTP_201_CREATED)


class ProjectImageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _image(self, request, pk):
        image = ProjectImage.objects.filter(pk=pk, project__in=visible_projects(request.user)).first()
        if image is None:
            raise NotFound('Image introuvable.')
        return image

    def get(self, request, pk):
        image = self._image(request, pk)
        response = HttpResponse(bytes(image.data), content_type=image.content_type)
        response['Cache-Control'] = 'private, max-age=86400'
        return response

    def delete(self, request, pk):
        image = self._image(request, pk)
        if image.project.user_id != request.user.id:
            raise PermissionDenied("Seul l'auteur du mémoire peut supprimer une image.")
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
