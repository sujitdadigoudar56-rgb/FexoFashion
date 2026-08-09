from django.urls import path

from . import views

urlpatterns = [
    path('checkout/', views.CheckoutAPIView.as_view(), name='checkout'),
    path('', views.OrderListAPIView.as_view(), name='order-list'),
    path('<str:order_number>/', views.OrderDetailAPIView.as_view(), name='order-detail'),
]
