from django.contrib.auth import get_user_model
from rest_framework import serializers

from categories.serializers import CategorySerializer, CollectionSerializer

from .models import Product, ProductImage, ProductReview, ProductVariant

User = get_user_model()


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'display_order']


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'size', 'stock_quantity', 'low_stock_threshold']


class ReviewUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name']


class ProductReviewSerializer(serializers.ModelSerializer):
    user = ReviewUserSerializer(read_only=True)

    class Meta:
        model = ProductReview
        fields = ['id', 'product', 'user', 'rating', 'title', 'comment', 'is_approved', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    """Full product representation — used for both list and detail
    responses. Deliberately carries only raw model fields (no
    is_on_sale/discount_percent/average_rating/etc.) — the frontend
    already derives all of those client-side in lib/product.ts, matching
    the same @property logic this model defines, so there's one source of
    truth for that math instead of two."""

    category = CategorySerializer(read_only=True)
    collections = CollectionSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'category', 'collections',
            'short_description', 'description', 'fabric_details', 'size_guide',
            'price', 'compare_at_price', 'gst_percent', 'color', 'available_sizes',
            'is_featured', 'is_trending', 'is_new_arrival', 'is_best_seller',
            'status', 'created_at', 'images', 'variants', 'reviews',
        ]

    def get_reviews(self, obj):
        approved = obj.reviews.filter(is_approved=True)
        return ProductReviewSerializer(approved, many=True, context=self.context).data
