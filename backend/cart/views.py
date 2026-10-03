from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Coupon
from products.models import Product, ProductVariant

from .models import Cart, CartItem
from .serializers import CartSerializer, parse_item_ids

# Cart is authenticated-only in this API — there's no session-cookie-based
# anonymous cart the way the original app had (that relied on Django
# session cookies, which the token-authenticated Next.js frontend doesn't
# send). Guests are prompted to sign in before adding to bag.


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


class CartAPIView(APIView):
    """GET /api/cart/"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart = _get_cart(request.user)
        context = {'request': request, 'selected_ids': parse_item_ids(request.query_params.get('items'))}
        return Response(CartSerializer(cart, context=context).data)


class CartAddAPIView(APIView):
    """POST /api/cart/add/<slug>/ { variant, quantity }"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, status='published')
        cart = _get_cart(request.user)
        variant_id = request.data.get('variant')
        try:
            quantity = int(request.data.get('quantity', 1) or 1)
        except (TypeError, ValueError):
            quantity = 1
        variant = ProductVariant.objects.filter(pk=variant_id, product=product).first() if variant_id else None

        item, created = CartItem.objects.get_or_create(cart=cart, product=product, variant=variant)
        item.quantity = quantity if created else item.quantity + quantity
        item.save()
        return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_201_CREATED)


class CartUpdateAPIView(APIView):
    """POST /api/cart/update/<item_id>/ { quantity }"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, item_id):
        cart = _get_cart(request.user)
        item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        try:
            quantity = int(request.data.get('quantity', 1) or 1)
        except (TypeError, ValueError):
            quantity = 1
        if quantity <= 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save()
        return Response(CartSerializer(cart, context={'request': request}).data)


class CartRemoveAPIView(APIView):
    """POST /api/cart/remove/<item_id>/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, item_id):
        cart = _get_cart(request.user)
        item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        item.delete()
        return Response(CartSerializer(cart, context={'request': request}).data)


class CartApplyCouponAPIView(APIView):
    """POST /api/cart/coupon/apply/ { code }"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cart = _get_cart(request.user)
        code = (request.data.get('code') or '').strip().upper()
        coupon = Coupon.objects.filter(code=code).first()
        if not coupon or not coupon.is_valid:
            return Response({'detail': 'That coupon is invalid or expired.'}, status=status.HTTP_400_BAD_REQUEST)
        cart.coupon = coupon
        cart.save()
        return Response(CartSerializer(cart, context={'request': request}).data)
