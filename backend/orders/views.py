from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Address
from cart.models import Cart
from products.models import ProductVariant

from .models import Order, OrderItem
from .serializers import CheckoutSerializer, OrderSerializer


class CheckoutAPIView(APIView):
    """POST /api/orders/checkout/ { shipping_address, billing_address, notes }
    — reads the signed-in user's server Cart and turns it into an Order,
    same transaction/stock-decrement flow as the original checkout_view.
    (order_success/order_detail no longer need separate "did I just place
    this" vs "look up an old one" views — both are just GET
    /api/orders/<order_number>/ now.)"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cart = Cart.objects.filter(user=request.user).first()
        if not cart or cart.items.count() == 0:
            return Response({'detail': 'Your bag is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        billing = get_object_or_404(Address, pk=serializer.validated_data['billing_address'], user=request.user)
        shipping = get_object_or_404(Address, pk=serializer.validated_data['shipping_address'], user=request.user)

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                billing_address=billing,
                shipping_address=shipping,
                subtotal=cart.subtotal,
                gst_amount=cart.gst_total,
                shipping_cost=cart.shipping_cost,
                discount_amount=cart.discount_amount,
                grand_total=cart.grand_total,
                coupon=cart.coupon,
                payment_method='cod',
                notes=serializer.validated_data.get('notes', ''),
            )

            for item in cart.items.select_related('product', 'variant'):
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    variant=item.variant,
                    product_name=item.product.name,
                    unit_price=item.product.price,
                    quantity=item.quantity,
                    size=item.variant.size if item.variant else '',
                )
                if item.variant:
                    variant = ProductVariant.objects.select_for_update().get(pk=item.variant.pk)
                    variant.stock_quantity = max(0, variant.stock_quantity - item.quantity)
                    variant.save()

            if order.coupon:
                order.coupon.times_used += 1
                order.coupon.save()

            cart.items.all().delete()
            cart.coupon = None
            cart.save()

        return Response(OrderSerializer(order, context={'request': request}).data, status=status.HTTP_201_CREATED)


class OrderListAPIView(generics.ListAPIView):
    """GET /api/orders/ — the signed-in user's own orders."""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderDetailAPIView(generics.RetrieveAPIView):
    """GET /api/orders/<order_number>/"""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'
    lookup_url_kwarg = 'order_number'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
