from decimal import Decimal

from django.conf import settings
from django.db import models

from products.models import Product, ProductVariant


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

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.all()), Decimal('0.00'))

    @property
    def gst_total(self):
        return sum((item.gst_amount for item in self.items.all()), Decimal('0.00'))

    @property
    def discount_amount(self):
        if self.coupon and self.coupon.is_valid:
            return self.coupon.calculate_discount(self.subtotal)
        return Decimal('0.00')

    @property
    def shipping_cost(self):
        if self.subtotal == 0 or self.subtotal >= Decimal('2999.00'):
            return Decimal('0.00')
        return Decimal('149.00')

    @property
    def grand_total(self):
        total = self.subtotal + self.gst_total + self.shipping_cost - self.discount_amount
        return total if total > 0 else Decimal('0.00')

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


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
