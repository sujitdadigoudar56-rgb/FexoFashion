from rest_framework import serializers

from products.models import Product

from .models import Cart, CartItem


class CartItemProductSerializer(serializers.ModelSerializer):
    """Lightweight product snapshot embedded in each cart line — just
    enough for the bag/checkout UI to render without a second request per
    item."""

    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'price', 'primary_image']

    def get_primary_image(self, obj):
        image = obj.primary_image
        if not image:
            return None
        request = self.context.get('request')
        url = image.image.url
        return request.build_absolute_uri(url) if request else url


class CartItemSerializer(serializers.ModelSerializer):
    product = CartItemProductSerializer(read_only=True)
    variant_size = serializers.SerializerMethodField()
    line_total = serializers.ReadOnlyField()
    gst_amount = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'variant', 'variant_size', 'quantity', 'line_total', 'gst_amount']

    def get_variant_size(self, obj):
        return obj.variant.size if obj.variant else None


class CartSerializer(serializers.ModelSerializer):
    """Mirrors cart/models.py's Cart properties directly — same GST/
    shipping/coupon math the old cart.html template used."""

    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.ReadOnlyField()
    gst_total = serializers.ReadOnlyField()
    shipping_cost = serializers.ReadOnlyField()
    discount_amount = serializers.ReadOnlyField()
    grand_total = serializers.ReadOnlyField()
    coupon_code = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id', 'items', 'subtotal', 'gst_total', 'shipping_cost',
            'discount_amount', 'grand_total', 'coupon_code',
        ]

    def get_coupon_code(self, obj):
        return obj.coupon.code if obj.coupon else None
