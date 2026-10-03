import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from accounts.models import Address
from products.models import Product, ProductVariant


class Coupon(models.Model):
    DISCOUNT_TYPE = [('percent', 'Percentage'), ('flat', 'Flat Amount')]

    code = models.CharField(max_length=30, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE, default='percent')
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    minimum_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    max_uses = models.PositiveIntegerField(default=0, help_text='0 = unlimited')
    times_used = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.max_uses and self.times_used >= self.max_uses:
            return False
        from django.utils import timezone
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def calculate_discount(self, subtotal):
        if subtotal < self.minimum_order_value:
            return Decimal('0.00')
        if self.discount_type == 'percent':
            return (subtotal * self.discount_value / Decimal('100')).quantize(Decimal('0.01'))
        return min(self.discount_value, subtotal)


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_CHOICES = [
        ('razorpay', 'Online (Razorpay)'),
        ('cod', 'Cash on Delivery'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    order_number = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')

    billing_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, related_name='billing_orders'
    )
    shipping_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, related_name='shipping_orders'
    )

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='cod')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')

    # Payment tracking. db_default keeps inserts from older app versions
    # (which don't know these columns) working during a rolling deploy.
    payment_status = models.CharField(
        max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending', db_default='pending'
    )
    razorpay_order_id = models.CharField(max_length=40, blank=True, default='', db_default='', db_index=True)
    razorpay_payment_id = models.CharField(max_length=40, blank=True, default='', db_default='')
    razorpay_signature = models.CharField(max_length=128, blank=True, default='', db_default='')
    razorpay_refund_id = models.CharField(max_length=40, blank=True, default='', db_default='')
    paid_at = models.DateTimeField(null=True, blank=True)
    # True once stock/coupon/bag have been settled for this order (at
    # placement for COD, after successful payment for Razorpay).
    is_finalized = models.BooleanField(default=False, db_default=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f'FEXO{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)

    @property
    def awaiting_payment(self):
        """An online order the customer hasn't paid for yet."""
        return self.payment_method == 'razorpay' and self.payment_status in ('pending', 'failed') and self.status != 'cancelled'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10, blank=True)

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f'{self.quantity} x {self.product_name}'
