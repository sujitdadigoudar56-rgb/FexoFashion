from django.urls import path
from . import views

app_name = 'wishlist'

urlpatterns = [
    path('', views.wishlist_view, name='wishlist'),
    path('toggle/<slug:slug>/', views.wishlist_toggle, name='wishlist_toggle'),
]
