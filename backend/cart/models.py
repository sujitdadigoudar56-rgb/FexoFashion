from decimal import Decimal

from django.conf import settings
from django.db import models

from products.models import Product, ProductVariant


FREE_SHIPPING_THRESHOLD = Decimal('2999.00')
FLAT_SHIPPING_COST = Decimal('149.00')


def compute_totals(items, coupon=None):
    """Subtotal/GST/shipping/discount/grand total for a set of cart items.
    Cart's properties use this for the whole cart; the bag page and
    checkout use it for just the items the customer selected."""
    items = list(items)
    subtotal = sum((item.line_total for item in items), Decimal('0.00'))
    gst_total = sum((item.gst_amount for item in items), Decimal('0.00'))
    discount = coupon.calculate_discount(subtotal) if coupon and coupon.is_valid and items else Decimal('0.00')
    shipping = Decimal('0.00') if subtotal == 0 or subtotal >= FREE_SHIPPING_THRESHOLD else FLAT_SHIPPING_COST
    grand_total = subtotal + gst_total + shipping - discount
    return {
        'subtotal': subtotal,
        'gst_total': gst_total,
        'shipping_cost': shipping,
        'discount_amount': discount,
        'grand_total': grand_total if grand_total > 0 else Decimal('0.00'),
        'item_count': sum(item.quantity for item in items),
    }


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='cart'
    )
    session_key = models.CharField(max_length=64, null=True, blank=True)
    coupon = models.ForeignKey('orders.Coupon', on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Cart #{self.pk}'

    def totals(self, items=None):
        return compute_totals(self.items.all() if items is None else items, self.coupon)

    @property
    def subtotal(self):
        return self.totals()['subtotal']

    @property
    def gst_total(self):
        return self.totals()['gst_total']

    @property
    def discount_amount(self):
        return self.totals()['discount_amount']

    @property
    def shipping_cost(self):
        return self.totals()['shipping_cost']

    @property
    def grand_total(self):
        return self.totals()['grand_total']

    @property
    def item_count(self):
        return self.totals()['item_count']


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product', 'variant')

    def __str__(self):
        return f'{self.quantity} x {self.product.name}'

    @property
    def line_total(self):
        return self.product.price * self.quantity

    @property
    def gst_amount(self):
        return (self.line_total * self.product.gst_percent / Decimal('100')).quantize(Decimal('0.01'))
