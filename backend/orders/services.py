"""Order lifecycle shared by checkout, the Razorpay callbacks/webhook and
the admin API.

COD:       place -> finalize immediately (stock, coupon, bag) -> paid when delivered
Razorpay:  place (pending payment, nothing reserved) -> customer pays ->
           signature + Razorpay API verified -> paid + confirmed + finalize
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from cart.models import Cart
from products.models import ProductVariant

from . import razorpay
from .models import Order, OrderItem

log = logging.getLogger(__name__)


class CheckoutError(Exception):
    pass


def check_stock(items):
    """items: cart items. Raises CheckoutError naming the first shortfall."""
    for item in items:
        if item.variant and item.variant.stock_quantity < item.quantity:
            left = item.variant.stock_quantity
            raise CheckoutError(
                f'Only {left} left of {item.product.name} in size {item.variant.size}.'
                if left else f'{item.product.name} in size {item.variant.size} is out of stock.'
            )


@transaction.atomic
def create_order(*, user, cart, items, totals, shipping, billing, notes, payment_method):
    check_stock(items)
    order = Order.objects.create(
        user=user,
        billing_address=billing,
        shipping_address=shipping,
        subtotal=totals['subtotal'],
        gst_amount=totals['gst_total'],
        shipping_cost=totals['shipping_cost'],
        discount_amount=totals['discount_amount'],
        grand_total=totals['grand_total'],
        coupon=cart.coupon if totals['discount_amount'] else None,
        payment_method=payment_method,
        payment_status='pending',
        is_finalized=False,
        notes=notes,
    )
    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,
            product_name=item.product.name,
            unit_price=item.product.price,
            quantity=item.quantity,
            size=item.variant.size if item.variant else '',
        )
    return order


@transaction.atomic
def finalize_order(order):
    """Deduct stock, use up the coupon and take the purchased lines out of
    the customer's bag. Idempotent."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.is_finalized:
        return order
    for item in order.items.select_related('variant'):
        if item.variant_id:
            variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
            variant.stock_quantity = max(0, variant.stock_quantity - item.quantity)
            variant.save(update_fields=['stock_quantity'])
    if order.coupon:
        order.coupon.times_used += 1
        order.coupon.save(update_fields=['times_used'])

    cart = Cart.objects.filter(user=order.user).first()
    if cart:
        for item in order.items.all():
            cart.items.filter(product_id=item.product_id, variant_id=item.variant_id).delete()
        if order.coupon or not cart.items.exists():
            cart.coupon = None
            cart.save(update_fields=['coupon'])

    order.is_finalized = True
    order.save(update_fields=['is_finalized', 'updated_at'])
    return order


@transaction.atomic
def restock(order):
    """Return a finalized order's units to stock (on cancellation)."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if not order.is_finalized:
        return
    for item in order.items.all():
        if item.variant_id:
            variant = ProductVariant.objects.select_for_update().filter(pk=item.variant_id).first()
            if variant:
                variant.stock_quantity += item.quantity
                variant.save(update_fields=['stock_quantity'])
    order.is_finalized = False
    order.save(update_fields=['is_finalized', 'updated_at'])


def ensure_razorpay_order(order):
    """Create (or reuse) the Razorpay order for this FEXO order."""
    if order.razorpay_order_id:
        return order.razorpay_order_id
    rzp = razorpay.create_order(
        order.grand_total,
        receipt=order.order_number,
        notes={'fexo_order': order.order_number, 'customer_email': order.user.email or ''},
    )
    order.razorpay_order_id = rzp['id']
    order.save(update_fields=['razorpay_order_id', 'updated_at'])
    return order.razorpay_order_id


def checkout_payload(order, request=None):
    """What the storefront needs to open Razorpay Checkout."""
    user = order.user
    phone = getattr(getattr(user, 'profile', None), 'phone', '') or (order.shipping_address.phone if order.shipping_address else '')
    return {
        'key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': order.razorpay_order_id,
        'amount': razorpay.to_paise(order.grand_total),
        'currency': 'INR',
        'name': 'FEXO',
        'description': f'Order {order.order_number}',
        'prefill': {
            'name': user.get_full_name() or user.username,
            'email': user.email,
            'contact': phone,
        },
    }


@transaction.atomic
def mark_paid(order, payment_id, signature=''):
    """Confirm a Razorpay payment against Razorpay's API, then mark the
    order paid/confirmed and finalize it. Raises CheckoutError when the
    payment doesn't check out. Safe to call twice (handler + webhook)."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.payment_status == 'paid':
        return order

    payment = razorpay.fetch_payment(payment_id)
    if payment.get('order_id') != order.razorpay_order_id:
        raise CheckoutError('This payment does not belong to this order.')
    expected = razorpay.to_paise(order.grand_total)
    if int(payment.get('amount', 0)) != expected or payment.get('currency') != 'INR':
        raise CheckoutError('The paid amount does not match the order total.')
    if payment.get('status') == 'authorized':
        payment = razorpay.capture_payment(payment_id, expected)
    if payment.get('status') != 'captured':
        raise CheckoutError(f"Payment is {payment.get('status', 'not complete')}.")

    order.payment_status = 'paid'
    order.razorpay_payment_id = payment_id
    if signature:
        order.razorpay_signature = signature
    order.paid_at = timezone.now()
    if order.status == 'pending':
        order.status = 'confirmed'
    order.save()
    finalize_order(order)
    return Order.objects.get(pk=order.pk)


def mark_failed(order):
    if order.payment_status == 'pending':
        order.payment_status = 'failed'
        order.save(update_fields=['payment_status', 'updated_at'])


def refund(order, reason=''):
    """Full refund of a paid Razorpay order."""
    if order.payment_method != 'razorpay' or order.payment_status != 'paid' or not order.razorpay_payment_id:
        raise CheckoutError('Only paid online orders can be refunded here.')
    result = razorpay.refund_payment(
        order.razorpay_payment_id,
        razorpay.to_paise(order.grand_total),
        notes={'fexo_order': order.order_number, 'reason': reason[:200]},
    )
    order.payment_status = 'refunded'
    order.razorpay_refund_id = result.get('id', '')
    order.save(update_fields=['payment_status', 'razorpay_refund_id', 'updated_at'])
    return order


def cancel(order, *, refund_payment=True):
    """Cancel an order: restock what was deducted and refund an online
    payment. Returns the refreshed order."""
    if order.status == 'cancelled':
        return order
    if refund_payment and order.payment_method == 'razorpay' and order.payment_status == 'paid':
        refund(order, reason='Order cancelled')
    restock(order)
    order.status = 'cancelled'
    order.save(update_fields=['status', 'updated_at'])
    return Order.objects.get(pk=order.pk)
