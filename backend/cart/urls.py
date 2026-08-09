from django.urls import path

from . import views

urlpatterns = [
    path('', views.CartAPIView.as_view(), name='cart-detail'),
    path('add/<slug:slug>/', views.CartAddAPIView.as_view(), name='cart-add'),
    path('update/<int:item_id>/', views.CartUpdateAPIView.as_view(), name='cart-update'),
    path('remove/<int:item_id>/', views.CartRemoveAPIView.as_view(), name='cart-remove'),
    path('coupon/apply/', views.CartApplyCouponAPIView.as_view(), name='cart-apply-coupon'),
]
