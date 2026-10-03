from rest_framework import serializers

from products.models import Product

from .models import Cart, CartItem


def parse_item_ids(value):
    """'1,2,3' or [1, 2, 3] -> {1, 2, 3}; None when no selection was given."""
    if value in (None, ''):
        return None
    raw = value if isinstance(value, (list, tuple)) else str(value).split(',')
    ids = set()
    for v in raw:
        try:
            ids.add(int(v))
        except (TypeError, ValueError):
            continue
    return ids


class CartItemProductSerializer(serializers.ModelSerializer):
    """Lightweight product snapshot embedded in each cart line — just
    enough for the bag/checkout UI to render without a second request per
    item."""

    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'price', 'compare_at_price', 'color', 'primary_image']

    def get_primary_image(self, obj):
        image = obj.primary_image
        if not image:
            return None
        request = self.context.get('request')
        url = image.image.url
        return request.build_absolute_uri(url) if request and url.startswith('/') else url


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

    items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    gst_total = serializers.SerializerMethodField()
    shipping_cost = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()
    coupon_code = serializers.SerializerMethodField()
    selection = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id', 'items', 'subtotal', 'gst_total', 'shipping_cost',
            'discount_amount', 'grand_total', 'coupon_code', 'selection',
        ]

    def to_representation(self, obj):
        # Load the lines once and compute every total from that list,
        # rather than re-querying the cart for each field.
        self._items = list(obj.items.select_related('product', 'variant').prefetch_related('product__images'))
        self._totals = obj.totals(self._items)
        return super().to_representation(obj)

    def get_items(self, obj):
        return CartItemSerializer(self._items, many=True, context=self.context).data

    def get_subtotal(self, obj):
        return self._totals['subtotal']

    def get_gst_total(self, obj):
        return self._totals['gst_total']

    def get_shipping_cost(self, obj):
        return self._totals['shipping_cost']

    def get_discount_amount(self, obj):
        return self._totals['discount_amount']

    def get_grand_total(self, obj):
        return self._totals['grand_total']

    def get_selection(self, obj):
        """Totals for just the items picked on the bag page (GET
        /api/cart/?items=1,2). Without a selection this matches the whole
        cart."""
        ids = self.context.get('selected_ids')
        items = self._items if ids is None else [i for i in self._items if i.id in ids]
        totals = obj.totals(items)
        totals['item_ids'] = [i.id for i in items]
        return totals

    def get_coupon_code(self, obj):
        return obj.coupon.code if obj.coupon else None
