from django.urls import path

from . import views

urlpatterns = [
    path('checkout/', views.CheckoutAPIView.as_view(), name='checkout'),
    path('', views.OrderListAPIView.as_view(), name='order-list'),
    path('<str:order_number>/', views.OrderDetailAPIView.as_view(), name='order-detail'),
    path('<str:order_number>/pay/', views.OrderPayAPIView.as_view(), name='order-pay'),
    path('<str:order_number>/verify-payment/', views.VerifyPaymentAPIView.as_view(), name='order-verify-payment'),
    path('<str:order_number>/payment-failed/', views.PaymentFailedAPIView.as_view(), name='order-payment-failed'),
    path('<str:order_number>/cancel/', views.OrderCancelAPIView.as_view(), name='order-cancel'),
]
