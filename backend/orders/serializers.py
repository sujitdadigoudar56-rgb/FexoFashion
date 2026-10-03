from rest_framework import serializers

from accounts.serializers import AddressSerializer

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_slug = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    line_total = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = [
            'product_slug', 'product_name', 'product_image', 'color',
            'unit_price', 'quantity', 'size', 'line_total',
        ]

    def get_product_image(self, obj):
        image = obj.product.primary_image if obj.product else None
        if not image or not image.image:
            return None
        url = image.image.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request and url.startswith('/') else url

    def get_color(self, obj):
        return obj.product.color if obj.product else ''

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
    awaiting_payment = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'order_number', 'billing_address', 'shipping_address',
            'subtotal', 'gst_amount', 'shipping_cost', 'discount_amount', 'grand_total',
            'coupon_code', 'payment_method', 'payment_status', 'awaiting_payment',
            'razorpay_payment_id', 'paid_at', 'status', 'notes', 'created_at', 'items',
        ]

    def get_coupon_code(self, obj):
        return obj.coupon.code if obj.coupon else None


class CheckoutSerializer(serializers.Serializer):
    shipping_address = serializers.IntegerField()
    billing_address = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)
    # Cart item ids to buy; omitted = the whole cart (previous behaviour).
    item_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=False)
    payment_method = serializers.ChoiceField(choices=['razorpay', 'cod'], required=False, default='cod')


class PaymentVerifySerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(max_length=40)
    razorpay_payment_id = serializers.CharField(max_length=40)
    razorpay_signature = serializers.CharField(max_length=128)
