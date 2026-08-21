from django.urls import path
from .search import SearchView

urlpatterns = [
    path('search/', SearchView.as_view(), name='documents_search'),
]
