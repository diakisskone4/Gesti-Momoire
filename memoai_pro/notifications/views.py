from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Notifications de l'utilisateur connecté (50 plus récentes).

    GET    /notifications/                  liste (+ ?unread=1)
    GET    /notifications/unread_count/     nombre de non lues
    POST   /notifications/<id>/mark_read/   marquer comme lue
    POST   /notifications/mark_all_read/    tout marquer comme lu
    DELETE /notifications/<id>/             supprimer
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger
            return Notification.objects.none()
        return Notification.objects.filter(recipient=self.request.user).select_related('actor')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        if request.query_params.get('unread') == '1':
            qs = qs.filter(read=False)
        return Response(self.get_serializer(qs[:50], many=True).data)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        return Response({'count': self.get_queryset().filter(read=False).count()})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        if not notif.read:
            notif.read = True
            notif.save(update_fields=['read'])
        return Response(self.get_serializer(notif).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(read=False).update(read=True)
        return Response({'updated': updated})
