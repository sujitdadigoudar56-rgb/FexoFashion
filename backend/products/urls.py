from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.shop_view, name='shop'),
    path('search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('category/<slug:slug>/', views.shop_by_category, name='shop_category'),
    path('collection/<slug:slug>/', views.shop_by_collection, name='shop_collection'),
    path('<slug:slug>/review/', views.add_review, name='add_review'),
    path('<slug:slug>/', views.product_detail, name='product_detail'),
]
