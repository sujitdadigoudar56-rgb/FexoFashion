from django.contrib import admin
from .models import Coupon, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'payment_method', 'grand_total', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('order_number', 'user__username', 'user__email')
    inlines = [OrderItemInline]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'is_active', 'times_used', 'max_uses')
    list_filter = ('is_active', 'discount_type')
