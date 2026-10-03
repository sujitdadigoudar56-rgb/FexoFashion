"""Serializers for the staff-only /api/admin/ endpoints.

Kept separate from each app's storefront serializers on purpose: the
storefront ones are read-only and hide fields (draft products, inactive
banners, unapproved reviews, etc.) that the admin needs to see and edit.
"""

from django.contrib.auth import get_user_model
from django.db.models import Sum
from rest_framework import serializers

from accounts.models import Address, Profile
from categories.models import Category, Collection
from orders.models import Coupon, Order, OrderItem
from products.models import Product, ProductImage, ProductReview, ProductVariant
from website.models import (
    FAQ,
    Banner,
    BlogPost,
    ContactMessage,
    InstagramPost,
    NewsletterSubscriber,
    SiteSettings,
    Testimonial,
)

User = get_user_model()


class StaffUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_superuser']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class AdminLoginSerializer(serializers.Serializer):
    # Accepts either the email address or the username.
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)


# --- Catalog -----------------------------------------------------------------

class AdminCategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'image', 'parent', 'parent_name',
            'is_active', 'display_order', 'meta_title', 'meta_description',
            'product_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {'slug': {'required': False}}


class AdminCollectionSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Collection
        fields = [
            'id', 'name', 'slug', 'description', 'banner_image', 'is_limited_drop',
            'is_active', 'start_date', 'end_date', 'product_count', 'created_at',
        ]
        read_only_fields = ['created_at']
        extra_kwargs = {'slug': {'required': False}}


class AdminProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image', 'alt_text', 'is_primary', 'display_order']


class AdminProductVariantSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id', 'product', 'size', 'stock_quantity', 'low_stock_threshold', 'is_low_stock']


class AdminProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    image = serializers.SerializerMethodField()
    total_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'category', 'category_name', 'price',
            'compare_at_price', 'status', 'total_stock', 'is_featured', 'is_trending',
            'is_new_arrival', 'is_best_seller', 'image', 'created_at', 'updated_at',
        ]

    def get_image(self, obj):
        img = obj.primary_image
        if not img or not img.image:
            return None
        request = self.context.get('request')
        url = img.image.url
        return request.build_absolute_uri(url) if request and url.startswith('/') else url


class AdminProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    collections = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Collection.objects.all(), required=False
    )
    images = AdminProductImageSerializer(many=True, read_only=True)
    variants = AdminProductVariantSerializer(many=True, read_only=True)
    total_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'category', 'category_name', 'collections',
            'short_description', 'description', 'fabric_details', 'size_guide',
            'price', 'compare_at_price', 'gst_percent', 'color', 'available_sizes',
            'is_featured', 'is_trending', 'is_new_arrival', 'is_best_seller',
            'status', 'meta_title', 'meta_description', 'total_stock',
            'images', 'variants', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {'slug': {'required': False, 'allow_blank': True}}


class AdminReviewSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = [
            'id', 'product', 'product_name', 'user', 'user_name', 'rating',
            'title', 'comment', 'is_approved', 'created_at',
        ]
        read_only_fields = ['product', 'user', 'rating', 'title', 'comment', 'created_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


# --- Orders & customers ------------------------------------------------------

class AdminAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'address_type', 'full_name', 'phone', 'line1', 'line2',
            'city', 'state', 'postal_code', 'country', 'is_default',
        ]


class AdminOrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True, default=None)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_slug', 'product_name', 'unit_price', 'quantity', 'size', 'line_total']


class OrderCustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class AdminOrderListSerializer(serializers.ModelSerializer):
    customer = OrderCustomerSerializer(source='user', read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    awaiting_payment = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'status', 'payment_method', 'payment_status',
            'awaiting_payment', 'grand_total', 'item_count', 'created_at',
        ]


class AdminOrderSerializer(serializers.ModelSerializer):
    customer = OrderCustomerSerializer(source='user', read_only=True)
    items = AdminOrderItemSerializer(many=True, read_only=True)
    billing_address = AdminAddressSerializer(read_only=True)
    shipping_address = AdminAddressSerializer(read_only=True)
    coupon_code = serializers.CharField(source='coupon.code', read_only=True, default=None)
    awaiting_payment = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'billing_address', 'shipping_address',
            'subtotal', 'gst_amount', 'shipping_cost', 'discount_amount', 'grand_total',
            'coupon_code', 'payment_method', 'payment_status', 'awaiting_payment',
            'razorpay_order_id', 'razorpay_payment_id', 'razorpay_refund_id', 'paid_at',
            'is_finalized', 'status', 'notes', 'items', 'created_at', 'updated_at',
        ]
        # Only fulfilment fields are editable — totals and line items are a
        # record of what the customer was charged. payment_status is
        # editable for cash on delivery only (online payments are set by
        # Razorpay).
        read_only_fields = [
            f for f in fields if f not in ('status', 'notes', 'payment_status')
        ]

    def validate(self, attrs):
        order = self.instance
        new_status = attrs.get('status', order.status)
        if 'payment_status' in attrs and attrs['payment_status'] != order.payment_status:
            if order.payment_method != 'cod':
                raise serializers.ValidationError({'payment_status': ['Online payment status is updated by Razorpay; use Refund to refund it.']})
            if attrs['payment_status'] not in ('pending', 'paid'):
                raise serializers.ValidationError({'payment_status': ['Cash on delivery can only be pending or paid.']})
        if order.awaiting_payment and new_status not in ('pending', 'cancelled'):
            raise serializers.ValidationError({'status': ["This online order hasn't been paid yet, so it can only be cancelled."]})
        if order.status == 'cancelled' and new_status != 'cancelled':
            raise serializers.ValidationError({'status': ['Cancelled orders cannot be reopened.']})
        return attrs


class AdminCustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    order_count = serializers.IntegerField(read_only=True)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'phone',
            'is_active', 'is_staff', 'date_joined', 'last_login', 'order_count', 'total_spent',
        ]
        read_only_fields = [
            'username', 'email', 'first_name', 'last_name', 'date_joined', 'last_login',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_phone(self, obj):
        profile = Profile.objects.filter(user=obj).first()
        return profile.phone if profile else ''


class AdminCustomerDetailSerializer(AdminCustomerSerializer):
    addresses = AdminAddressSerializer(many=True, read_only=True)
    orders = serializers.SerializerMethodField()

    class Meta(AdminCustomerSerializer.Meta):
        fields = AdminCustomerSerializer.Meta.fields + ['addresses', 'orders']

    def get_orders(self, obj):
        qs = obj.orders.all()[:50]
        return [
            {
                'order_number': o.order_number,
                'status': o.status,
                'grand_total': o.grand_total,
                'created_at': o.created_at,
            }
            for o in qs
        ]


class AdminCouponSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'discount_type', 'discount_value', 'minimum_order_value',
            'max_uses', 'times_used', 'is_active', 'valid_from', 'valid_until',
            'is_valid', 'created_at',
        ]
        read_only_fields = ['times_used', 'created_at']

    def validate_code(self, value):
        return value.strip().upper()


# --- Website content ---------------------------------------------------------

class AdminBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['id', 'title', 'subtitle', 'image', 'video', 'link_url', 'is_active', 'display_order']


class AdminTestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = ['id', 'author_name', 'author_title', 'quote', 'rating', 'is_active']


class AdminInstagramPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstagramPost
        fields = ['id', 'image', 'link_url', 'is_active', 'display_order']


class AdminBlogPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content', 'cover_image',
            'author_name', 'is_published', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {'slug': {'required': False, 'allow_blank': True}}


class AdminFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer', 'display_order', 'is_active']


class AdminContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'is_read', 'created_at']
        read_only_fields = ['name', 'email', 'subject', 'message', 'created_at']


class AdminNewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ['id', 'email', 'subscribed_at']
        read_only_fields = ['subscribed_at']


class AdminSiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = [
            'site_name', 'tagline', 'contact_email', 'contact_phone', 'address',
            'instagram_url', 'facebook_url', 'twitter_url',
        ]


def customer_totals(queryset):
    """Annotate a User queryset with order_count / total_spent (cancelled
    orders excluded from the spend)."""
    from django.db.models import Count, DecimalField, Q, Value
    from django.db.models.functions import Coalesce

    return queryset.annotate(
        order_count=Count('orders', distinct=True),
        total_spent=Coalesce(
            Sum('orders__grand_total', filter=~Q(orders__status='cancelled')),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    )
