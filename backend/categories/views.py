from rest_framework.generics import ListAPIView, RetrieveAPIView

from .models import Category, Collection
from .serializers import CategorySerializer, CollectionSerializer


class CategoryListAPIView(ListAPIView):
    """GET /api/categories/ — active categories, unpaginated (small list,
    used to populate nav/shop-filter UI)."""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    pagination_class = None


class CategoryDetailAPIView(RetrieveAPIView):
    """GET /api/categories/<slug>/"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    lookup_field = 'slug'


class CollectionDetailAPIView(RetrieveAPIView):
    """GET /api/collections/<slug>/"""
    queryset = Collection.objects.filter(is_active=True)
    serializer_class = CollectionSerializer
    lookup_field = 'slug'
