from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=True)
router.register('categories', views.CategoryViewSet, basename='admin-category')
router.register('collections', views.CollectionViewSet, basename='admin-collection')
router.register('products', views.ProductViewSet, basename='admin-product')
router.register('product-images', views.ProductImageViewSet, basename='admin-product-image')
router.register('product-variants', views.ProductVariantViewSet, basename='admin-product-variant')
router.register('reviews', views.ReviewViewSet, basename='admin-review')
router.register('orders', views.OrderViewSet, basename='admin-order')
router.register('customers', views.CustomerViewSet, basename='admin-customer')
router.register('coupons', views.CouponViewSet, basename='admin-coupon')
router.register('banners', views.BannerViewSet, basename='admin-banner')
router.register('testimonials', views.TestimonialViewSet, basename='admin-testimonial')
router.register('instagram-posts', views.InstagramPostViewSet, basename='admin-instagram-post')
router.register('journal', views.BlogPostViewSet, basename='admin-blogpost')
router.register('faqs', views.FAQViewSet, basename='admin-faq')
router.register('messages', views.ContactMessageViewSet, basename='admin-message')
router.register('subscribers', views.NewsletterSubscriberViewSet, basename='admin-subscriber')

urlpatterns = [
    path('auth/login/', views.AdminLoginAPIView.as_view(), name='admin-login'),
    path('auth/logout/', views.AdminLogoutAPIView.as_view(), name='admin-logout'),
    path('auth/me/', views.AdminMeAPIView.as_view(), name='admin-me'),
    path('stats/', views.DashboardStatsAPIView.as_view(), name='admin-stats'),
    path('site-settings/', views.SiteSettingsAPIView.as_view(), name='admin-site-settings'),
    path('', include(router.urls)),
]
