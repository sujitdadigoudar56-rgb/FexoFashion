from django.contrib import admin
from .models import Category, Collection


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'display_order')
    list_filter = ('is_active', 'parent')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_limited_drop', 'is_active', 'start_date', 'end_date')
    list_filter = ('is_limited_drop', 'is_active')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
