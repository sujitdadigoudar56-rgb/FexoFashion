from django.urls import path

from . import views

urlpatterns = [
    path('', views.CategoryListAPIView.as_view(), name='category-list'),
    path('<slug:slug>/', views.CategoryDetailAPIView.as_view(), name='category-detail'),
]
