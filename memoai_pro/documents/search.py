from django.db.models import Q
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.access import visible_projects


class SearchView(APIView):
    """Recherche plein texte simple, limitée aux mémoires que l'utilisateur peut voir."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'results': []})

        queryset = visible_projects(request.user).filter(
            Q(title__icontains=query)
            | Q(theme__icontains=query)
            | Q(university__icontains=query)
            | Q(field_of_study__icontains=query)
        ).values('id', 'title', 'status')[:20]

        return Response({'results': [
            {'id': p['id'], 'title': p['title'], 'status': p['status'], 'score': 1.0} for p in queryset
        ]})
