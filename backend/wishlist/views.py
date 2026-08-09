from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product
from products.serializers import ProductSerializer

from .models import Wishlist, WishlistItem


def _get_wishlist(user):
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return wishlist


def _serialize_items(wishlist, request):
    products = [item.product for item in wishlist.items.select_related('product').all()]
    return ProductSerializer(products, many=True, context={'request': request}).data


class WishlistAPIView(APIView):
    """GET /api/wishlist/ — full Product objects, not just ids, so the
    frontend can render the wishlist page directly from this response."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        wishlist = _get_wishlist(request.user)
        return Response(_serialize_items(wishlist, request))


class WishlistToggleAPIView(APIView):
    """POST /api/wishlist/toggle/<slug>/ — add if absent, remove if
    present; returns whether it was added plus the updated item list."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        wishlist = _get_wishlist(request.user)
        item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
        if not created:
            item.delete()
        return Response({
            'added': created,
            'items': _serialize_items(wishlist, request),
        })
