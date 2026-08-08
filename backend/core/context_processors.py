from decimal import Decimal

from django.db.models import Sum


def admin_dashboard_stats(request):
    """Live storefront stats surfaced on the FEXO admin dashboard homepage.
    Only queries when a staff user is viewing /admin/, to avoid extra
    queries on every public page load."""
    if not (request.path.startswith('/admin/') and request.user.is_authenticated and request.user.is_staff):
        return {}

    from django.contrib.auth import get_user_model
    from orders.models import Order
    from products.models import Product

    User = get_user_model()
    revenue = Order.objects.exclude(status='cancelled').aggregate(total=Sum('grand_total'))['total'] or Decimal('0.00')

    return {
        'fexo_stats': {
            'product_count': Product.objects.filter(status='published').count(),
            'order_count': Order.objects.count(),
            'revenue': revenue,
            'customer_count': User.objects.filter(is_staff=False).count(),
        }
    }
