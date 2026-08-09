from rest_framework import serializers

from .models import Category, Collection


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'image', 'parent',
            'is_active', 'display_order',
        ]


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = [
            'id', 'name', 'slug', 'description', 'banner_image',
            'is_limited_drop', 'is_active',
        ]
