from rest_framework import serializers

from accounts.serializers import AddressSerializer

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_slug = serializers.SerializerMethodField()
    line_total = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ['product_slug', 'product_name', 'unit_price', 'quantity', 'size', 'line_total']

    def get_product_slug(self, obj):
        # product is SET_NULL on delete, so it can legitimately be gone —
        # product_name/unit_price/size are already snapshotted onto the
        # OrderItem itself for exactly this reason.
        return obj.product.slug if obj.product else ''


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    billing_address = AddressSerializer(read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    coupon_code = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'order_number', 'billing_address', 'shipping_address',
            'subtotal', 'gst_amount', 'shipping_cost', 'discount_amount', 'grand_total',
            'coupon_code', 'payment_method', 'status', 'notes', 'created_at', 'items',
        ]

    def get_coupon_code(self, obj):
        return obj.coupon.code if obj.coupon else None


class CheckoutSerializer(serializers.Serializer):
    shipping_address = serializers.IntegerField()
    billing_address = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)
