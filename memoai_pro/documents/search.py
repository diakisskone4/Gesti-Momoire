from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from projects.models import Project

class SearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'results': []})

        queryset = Project.objects.filter(
            Q(title__icontains=query)
            | Q(theme__icontains=query)
            | Q(university__icontains=query)
            | Q(field_of_study__icontains=query)
        ).values('id', 'title')[:20]

        results = [
            {'id': item['id'], 'title': item['title'], 'score': 1.0}
            for item in queryset
        ]

        return Response({'results': results})