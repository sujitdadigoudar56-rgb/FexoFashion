from django.urls import path

from . import views

urlpatterns = [
    path('', views.WishlistAPIView.as_view(), name='wishlist-detail'),
    path('toggle/<slug:slug>/', views.WishlistToggleAPIView.as_view(), name='wishlist-toggle'),
]
