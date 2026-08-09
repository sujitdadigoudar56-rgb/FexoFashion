from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

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

if settings.DEBUG:
    # Static assets (django.contrib.admin's own CSS/JS) are auto-served by
    # runserver via django.contrib.staticfiles — only media (uploaded
    # product/category images etc.) needs this explicit dev route.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'FEXO Admin'
admin.site.site_title = 'FEXO Admin Portal'
admin.site.index_title = 'Dashboard'
