from django.urls import path

from . import views

urlpatterns = [
    path('', views.ProductListAPIView.as_view(), name='product-list'),
    path('facets/', views.ProductFacetsAPIView.as_view(), name='product-facets'),
    path('search-suggestions/', views.SearchSuggestionsAPIView.as_view(), name='product-search-suggestions'),
    path('<slug:slug>/review/', views.AddReviewAPIView.as_view(), name='product-add-review'),
    path('<slug:slug>/', views.ProductDetailAPIView.as_view(), name='product-detail'),
]
