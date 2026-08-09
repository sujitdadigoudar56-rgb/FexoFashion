from django.urls import path

from . import views

urlpatterns = [
    path('banners/', views.BannerListAPIView.as_view(), name='banner-list'),
    path('testimonials/', views.TestimonialListAPIView.as_view(), name='testimonial-list'),
    path('instagram-posts/', views.InstagramPostListAPIView.as_view(), name='instagram-post-list'),
    path('journal/', views.BlogPostListAPIView.as_view(), name='blogpost-list'),
    path('journal/<slug:slug>/', views.BlogPostDetailAPIView.as_view(), name='blogpost-detail'),
    path('faqs/', views.FAQListAPIView.as_view(), name='faq-list'),
    path('site-settings/', views.SiteSettingsAPIView.as_view(), name='site-settings'),
    path('contact/', views.ContactCreateAPIView.as_view(), name='contact-create'),
    path('newsletter/', views.NewsletterCreateAPIView.as_view(), name='newsletter-create'),
]
