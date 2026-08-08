from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('faq/', views.faq_view, name='faq'),
    path('journal/', views.journal_view, name='journal'),
    path('journal/<slug:slug>/', views.journal_detail_view, name='journal_detail'),
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('terms/', views.terms_view, name='terms'),
    path('shipping/', views.shipping_view, name='shipping'),
    path('returns/', views.returns_view, name='returns'),
    path('newsletter/', views.newsletter_signup, name='newsletter_signup'),
]
