from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('me/', views.MeAPIView.as_view(), name='me'),
    path('me/avatar/', views.AvatarUploadAPIView.as_view(), name='me-avatar'),
    path('password/change/', views.ChangePasswordAPIView.as_view(), name='password-change'),

    path('password-reset/', views.PasswordResetRequestAPIView.as_view(), name='password-reset'),
    path('password-reset/confirm/', views.PasswordResetConfirmAPIView.as_view(), name='password-reset-confirm'),

    path('addresses/', views.AddressListCreateAPIView.as_view(), name='address-list'),
    path('addresses/<int:pk>/', views.AddressDetailAPIView.as_view(), name='address-detail'),
]
