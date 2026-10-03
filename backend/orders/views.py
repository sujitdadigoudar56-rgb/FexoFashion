import json
import logging

from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Address
from cart.models import Cart

from . import razorpay, services
from .models import Order
from .serializers import CheckoutSerializer, OrderSerializer, PaymentVerifySerializer

log = logging.getLogger(__name__)


def _order_response(order, request, extra=None, code=status.HTTP_200_OK):
    # Order fields stay at the top level (what older storefront builds
    # read); Razorpay checkout details ride alongside under `razorpay`.
    data = {**OrderSerializer(order, context={'request': request}).data, **(extra or {})}
    return Response(data, status=code)


class CheckoutAPIView(APIView):
    """POST /api/orders/checkout/
    { shipping_address, billing_address, notes, item_ids?, payment_method }

    payment_method "razorpay": creates the order awaiting payment
    and a Razorpay order; responds with `razorpay` checkout details. Stock,
    coupon and bag are only settled once the payment is verified.
    payment_method "cod" (the default when omitted, for older clients): the
    order is placed and settled immediately.

    Response: the order, plus `razorpay` checkout details for online payment."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cart = Cart.objects.filter(user=request.user).first()
        if not cart or cart.items.count() == 0:
            return Response({'detail': 'Your bag is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        billing = get_object_or_404(Address, pk=data['billing_address'], user=request.user)
        shipping = get_object_or_404(Address, pk=data['shipping_address'], user=request.user)

        items = list(cart.items.select_related('product', 'variant'))
        if data.get('item_ids'):
            wanted = set(data['item_ids'])
            items = [i for i in items if i.id in wanted]
            if not items:
                return Response({'detail': 'None of the selected items are in your bag.'}, status=status.HTTP_400_BAD_REQUEST)

        method = data['payment_method']
        if method == 'razorpay' and not razorpay.is_configured():
            return Response({'detail': 'Online payment is unavailable right now. Please choose cash on delivery.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = services.create_order(
                user=request.user, cart=cart, items=items, totals=cart.totals(items),
                shipping=shipping, billing=billing, notes=data.get('notes', ''), payment_method=method,
            )
        except services.CheckoutError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if method == 'cod':
            order = services.finalize_order(order)
            return _order_response(order, request, code=status.HTTP_201_CREATED)

        try:
            services.ensure_razorpay_order(order)
        except razorpay.RazorpayError as exc:
            log.warning('Razorpay order creation failed for %s: %s', order.order_number, exc)
            order.delete()
            return Response({'detail': f'Could not start the online payment: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)
        return _order_response(order, request, {'razorpay': services.checkout_payload(order)}, status.HTTP_201_CREATED)


class OrderPayAPIView(APIView):
    """POST /api/orders/<order_number>/pay/ — (re)open payment for an
    online order that hasn't been paid yet."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if not order.awaiting_payment:
            return Response({'detail': 'This order does not need payment.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            services.check_stock([i for i in order.items.select_related('variant', 'product') if i.product_id])
            services.ensure_razorpay_order(order)
        except services.CheckoutError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except razorpay.RazorpayError as exc:
            return Response({'detail': f'Could not start the online payment: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)
        if order.payment_status == 'failed':
            order.payment_status = 'pending'
            order.save(update_fields=['payment_status', 'updated_at'])
        return _order_response(order, request, {'razorpay': services.checkout_payload(order)})


class VerifyPaymentAPIView(APIView):
    """POST /api/orders/<order_number>/verify-payment/
    { razorpay_order_id, razorpay_payment_id, razorpay_signature } — the
    values Razorpay Checkout hands the success callback."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data['razorpay_order_id'] != order.razorpay_order_id or not razorpay.verify_payment_signature(
            data['razorpay_order_id'], data['razorpay_payment_id'], data['razorpay_signature']
        ):
            services.mark_failed(order)
            return Response({'detail': 'Payment verification failed.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            order = services.mark_paid(order, data['razorpay_payment_id'], data['razorpay_signature'])
        except (services.CheckoutError, razorpay.RazorpayError) as exc:
            log.warning('Payment check failed for %s: %s', order.order_number, exc)
            return Response({'detail': f'Payment could not be confirmed: {exc}'}, status=status.HTTP_400_BAD_REQUEST)
        return _order_response(order, request)


class PaymentFailedAPIView(APIView):
    """POST /api/orders/<order_number>/payment-failed/ — the customer's
    payment attempt failed (Razorpay `payment.failed` in the browser)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if order.awaiting_payment:
            services.mark_failed(order)
        return _order_response(order, request)


class OrderCancelAPIView(APIView):
    """POST /api/orders/<order_number>/cancel/ — customers can cancel an
    order until it has been confirmed/shipped (unpaid online orders, or
    COD orders still pending)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if order.status != 'pending' or order.payment_status in ('paid', 'refunded'):
            return Response(
                {'detail': 'This order can no longer be cancelled online. Please contact support.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order = services.cancel(order)
        return _order_response(order, request)


class OrderListAPIView(generics.ListAPIView):
    """GET /api/orders/ — the signed-in user's own orders."""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__product__images')


class OrderDetailAPIView(generics.RetrieveAPIView):
    """GET /api/orders/<order_number>/"""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'
    lookup_url_kwarg = 'order_number'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


@csrf_exempt
def razorpay_webhook(request):
    """POST /api/payments/razorpay/webhook/ — Razorpay server-to-server
    events. Backs up the browser callback (e.g. the customer closed the
    tab right after paying). Requires RAZORPAY_WEBHOOK_SECRET."""
    from django.http import HttpResponse, JsonResponse

    if request.method != 'POST':
        return HttpResponse(status=405)
    if not razorpay.verify_webhook_signature(request.body, request.headers.get('X-Razorpay-Signature', '')):
        return HttpResponse(status=400)
    try:
        event = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)

    name = event.get('event', '')
    payment = event.get('payload', {}).get('payment', {}).get('entity', {})
    rzp_order_id = payment.get('order_id') or event.get('payload', {}).get('order', {}).get('entity', {}).get('id')
    order = Order.objects.filter(razorpay_order_id=rzp_order_id).first() if rzp_order_id else None
    if order is None:
        return JsonResponse({'status': 'ignored'})

    try:
        if name in ('payment.captured', 'payment.authorized', 'order.paid') and payment.get('id'):
            services.mark_paid(order, payment['id'])
        elif name == 'payment.failed':
            services.mark_failed(order)
        elif name == 'refund.processed' and order.payment_status == 'paid':
            order.payment_status = 'refunded'
            order.razorpay_refund_id = event.get('payload', {}).get('refund', {}).get('entity', {}).get('id', '')
            order.save(update_fields=['payment_status', 'razorpay_refund_id', 'updated_at'])
    except (services.CheckoutError, razorpay.RazorpayError) as exc:
        log.warning('Webhook %s for %s not applied: %s', name, order.order_number, exc)
    return JsonResponse({'status': 'ok'})
