from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from categories.views import CollectionDetailAPIView
from core.views import healthcheck

urlpatterns = [
    path('healthz/', healthcheck, name='healthcheck'),
    path('admin/', admin.site.urls),

    # JSON API consumed by the Next.js frontend (Fexo_Frontend). Django no
    # longer renders the storefront itself — only /admin/ still uses
    # server-rendered templates.
    path('api/accounts/', include('accounts.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/wishlist/', include('wishlist.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/products/', include('products.urls')),
    path('api/categories/', include('categories.urls')),
    path('api/collections/<slug:slug>/', CollectionDetailAPIView.as_view(), name='collection-detail'),
    path('api/', include('website.urls')),
]

# Static assets (django.contrib.admin's own CSS/JS) are auto-served by
# runserver in dev, and by whitenoise in production — only media (uploaded
# product/category images etc.) needs an explicit route, and unlike
# django.conf.urls.static.static() this one isn't disabled when DEBUG=False:
# there's no separate object-storage/CDN in front of media/ here, so Django
# itself has to keep serving it in production too.
# Skipped entirely when USE_S3=True — uploads live in the bucket then, and
# ImageField.url already points straight at S3, so nothing under /media/ on
# this host is ever real.
if not settings.USE_S3:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

admin.site.site_header = 'FEXO Admin'
admin.site.site_title = 'FEXO Admin Portal'
admin.site.index_title = 'Dashboard'
