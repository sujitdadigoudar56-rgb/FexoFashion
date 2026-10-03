"""Staff-only JSON API behind the separate Next.js admin app (Fexo-admin).

Everything here is mounted under /api/admin/ and requires an active
is_staff user authenticated with a DRF token (Authorization: Token <t>),
the same token scheme the storefront uses.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import authenticate, get_user_model
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from categories.models import Category, Collection
from orders import razorpay as rzp
from orders import services as order_services
from orders.models import Coupon, Order, OrderItem
from products.models import Product, ProductImage, ProductReview, ProductVariant
from website.models import (
    FAQ,
    Banner,
    BlogPost,
    ContactMessage,
    InstagramPost,
    NewsletterSubscriber,
    SiteSettings,
    Testimonial,
)

from . import serializers as s
from .pagination import AdminPagination
from .permissions import IsStaff

User = get_user_model()

# Orders in these states don't count towards revenue.
NON_REVENUE_STATUSES = ('cancelled',)


def revenue_queryset():
    """Orders that are real sales: not cancelled, not refunded, and — for
    online payments — actually paid."""
    return (
        Order.objects.exclude(status__in=NON_REVENUE_STATUSES)
        .exclude(payment_status='refunded')
        .exclude(payment_method='razorpay', payment_status__in=('pending', 'failed'))
    )


# --- Auth --------------------------------------------------------------------

class AdminLoginAPIView(APIView):
    """POST /api/admin/auth/login/ { email, password } — email or username.
    Only staff accounts get a token back; customers are rejected with the
    same message as a wrong password so the endpoint doesn't reveal which
    emails belong to staff."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = s.AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data['email'].strip()
        password = serializer.validated_data['password']

        username = identifier
        if '@' in identifier:
            match = User.objects.filter(email__iexact=identifier).order_by('-is_staff', 'pk').first()
            if match:
                username = match.get_username()

        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active or not user.is_staff:
            return Response(
                {'detail': 'Invalid credentials or this account does not have admin access.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': s.StaffUserSerializer(user).data})


class AdminMeAPIView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        return Response(s.StaffUserSerializer(request.user).data)


class AdminLogoutAPIView(APIView):
    permission_classes = [IsStaff]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Dashboard stats ---------------------------------------------------------

class DashboardStatsAPIView(APIView):
    """GET /api/admin/stats/?days=30 — KPI tiles, daily sales series,
    order status breakdown, top products, recent orders and low stock."""

    permission_classes = [IsStaff]

    def get(self, request):
        try:
            days = max(1, min(365, int(request.query_params.get('days', 30))))
        except ValueError:
            days = 30

        now = timezone.now()
        start = now - timedelta(days=days)
        prev_start = start - timedelta(days=days)

        revenue_orders = revenue_queryset()

        def period(qs, a, b):
            agg = qs.filter(created_at__gte=a, created_at__lt=b).aggregate(
                revenue=Sum('grand_total'), orders=Count('id')
            )
            return agg['revenue'] or Decimal('0'), agg['orders']

        revenue, orders = period(revenue_orders, start, now)
        prev_revenue, prev_orders = period(revenue_orders, prev_start, start)

        customers_qs = User.objects.filter(is_staff=False)
        new_customers = customers_qs.filter(date_joined__gte=start).count()
        prev_new_customers = customers_qs.filter(date_joined__gte=prev_start, date_joined__lt=start).count()

        def change(cur, prev):
            if not prev:
                return None
            return round((float(cur) - float(prev)) / float(prev) * 100, 1)

        daily = {
            row['day']: row
            for row in revenue_orders.filter(created_at__gte=start)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(revenue=Sum('grand_total'), orders=Count('id'))
        }
        series = []
        for i in range(days, -1, -1):
            day = (now - timedelta(days=i)).date()
            row = daily.get(day)
            series.append({
                'date': day.isoformat(),
                'revenue': float(row['revenue']) if row else 0,
                'orders': row['orders'] if row else 0,
            })

        # Unpaid online orders aren't real orders yet; keep them out of the
        # fulfilment pipeline counts.
        placed = Order.objects.exclude(payment_method='razorpay', payment_status__in=('pending', 'failed'), status='pending')
        by_status = {row['status']: row['n'] for row in placed.values('status').annotate(n=Count('id'))}
        status_breakdown = [
            {'status': key, 'label': label, 'count': by_status.get(key, 0)}
            for key, label in Order.STATUS_CHOICES
        ]

        top_products = list(
            OrderItem.objects.filter(order__created_at__gte=start, order__in=revenue_queryset())
            .values('product_id', 'product_name')
            .annotate(
                units=Sum('quantity'),
                revenue=Sum(ExpressionWrapper(
                    F('unit_price') * F('quantity'),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )),
            )
            .order_by('-revenue')[:5]
        )

        recent_orders = s.AdminOrderListSerializer(
            Order.objects.select_related('user').annotate(item_count=Sum('items__quantity'))[:6],
            many=True,
        ).data

        low_stock = [
            {
                'product_id': v.product_id,
                'product_name': v.product.name,
                'sku': v.product.sku,
                'size': v.size,
                'stock_quantity': v.stock_quantity,
                'low_stock_threshold': v.low_stock_threshold,
            }
            for v in ProductVariant.objects.select_related('product')
            .filter(stock_quantity__lte=F('low_stock_threshold'))
            .order_by('stock_quantity', 'product__name')[:8]
        ]

        return Response({
            'days': days,
            'kpis': {
                'revenue': float(revenue),
                'revenue_change': change(revenue, prev_revenue),
                'orders': orders,
                'orders_change': change(orders, prev_orders),
                'avg_order_value': float(revenue / orders) if orders else 0,
                'new_customers': new_customers,
                'new_customers_change': change(new_customers, prev_new_customers),
                'total_customers': customers_qs.count(),
                'total_products': Product.objects.count(),
                'published_products': Product.objects.filter(status='published').count(),
                'pending_orders': by_status.get('pending', 0),
                'unread_messages': ContactMessage.objects.filter(is_read=False).count(),
                'pending_reviews': ProductReview.objects.filter(is_approved=False).count(),
                'awaiting_payment': Order.objects.filter(
                    payment_method='razorpay', payment_status__in=('pending', 'failed'), status='pending'
                ).count(),
            },
            'sales': series,
            'status_breakdown': status_breakdown,
            'top_products': [
                {**row, 'revenue': float(row['revenue'] or 0)} for row in top_products
            ],
            'recent_orders': recent_orders,
            'low_stock': low_stock,
        })


# --- Generic viewset base ----------------------------------------------------

class AdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaff]
    pagination_class = AdminPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # Simple ?field=value equality filters, applied when present.
    filter_fields = ()

    def get_queryset(self):
        qs = super().get_queryset()
        for field in self.filter_fields:
            value = self.request.query_params.get(field)
            if value in (None, ''):
                continue
            if value in ('true', 'false'):
                value = value == 'true'
            qs = qs.filter(**{field: value})
        return qs

    def paginate_queryset(self, queryset):
        # ?page_size=all returns everything (for dropdowns).
        if self.request.query_params.get('page_size') == 'all':
            return None
        return super().paginate_queryset(queryset)


# --- Catalog -----------------------------------------------------------------

class CategoryViewSet(AdminViewSet):
    queryset = Category.objects.select_related('parent').annotate(product_count=Count('products'))
    serializer_class = s.AdminCategorySerializer
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'display_order', 'created_at', 'product_count']
    ordering = ['display_order', 'name']
    filter_fields = ('is_active', 'parent')

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        if category.products.exists():
            return Response(
                {'detail': 'This category still has products. Move or delete them first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class CollectionViewSet(AdminViewSet):
    queryset = Collection.objects.annotate(product_count=Count('products'))
    serializer_class = s.AdminCollectionSerializer
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'created_at', 'start_date']
    ordering = ['-created_at']
    filter_fields = ('is_active', 'is_limited_drop')


class ProductViewSet(AdminViewSet):
    queryset = (
        Product.objects.select_related('category')
        .prefetch_related('images', 'variants', 'collections')
    )
    search_fields = ['name', 'sku', 'slug']
    ordering_fields = ['name', 'price', 'created_at', 'updated_at']
    ordering = ['-created_at']
    filter_fields = (
        'status', 'category', 'is_featured', 'is_trending', 'is_new_arrival', 'is_best_seller',
    )

    def get_serializer_class(self):
        return s.AdminProductListSerializer if self.action == 'list' else s.AdminProductSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        stock = self.request.query_params.get('stock')
        if stock == 'out':
            qs = qs.annotate(_stock=Sum('variants__stock_quantity')).filter(
                Q(_stock__lte=0) | Q(_stock__isnull=True)
            )
        elif stock == 'low':
            qs = qs.filter(
                variants__stock_quantity__gt=0,
                variants__stock_quantity__lte=F('variants__low_stock_threshold'),
            ).distinct()
        return qs

    def perform_create(self, serializer):
        product = serializer.save()
        # Give every listed size a variant row so stock can be edited.
        for size in product.sizes_list:
            ProductVariant.objects.get_or_create(product=product, size=size)


class ProductImageViewSet(AdminViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = s.AdminProductImageSerializer
    pagination_class = None
    filter_fields = ('product',)
    ordering = ['display_order', 'id']

    def _ensure_single_primary(self, image):
        if image.is_primary:
            ProductImage.objects.filter(product=image.product).exclude(pk=image.pk).update(is_primary=False)

    def perform_create(self, serializer):
        product = serializer.validated_data['product']
        is_first = not product.images.exists()
        image = serializer.save(is_primary=serializer.validated_data.get('is_primary', False) or is_first)
        self._ensure_single_primary(image)

    def perform_update(self, serializer):
        self._ensure_single_primary(serializer.save())


class ProductVariantViewSet(AdminViewSet):
    queryset = ProductVariant.objects.select_related('product')
    serializer_class = s.AdminProductVariantSerializer
    pagination_class = None
    filter_fields = ('product',)
    ordering = ['id']


class ReviewViewSet(AdminViewSet):
    queryset = ProductReview.objects.select_related('product', 'user')
    serializer_class = s.AdminReviewSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
    search_fields = ['product__name', 'user__username', 'title', 'comment']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    filter_fields = ('is_approved', 'rating', 'product')


# --- Orders & customers ------------------------------------------------------

class OrderViewSet(AdminViewSet):
    queryset = (
        Order.objects.select_related('user', 'coupon', 'billing_address', 'shipping_address')
        .prefetch_related('items__product')
        .annotate(item_count=Sum('items__quantity'))
    )
    lookup_field = 'order_number'
    # POST is only routed to the `refund` action (no create route exists).
    http_method_names = ['get', 'patch', 'post', 'head', 'options']
    search_fields = ['order_number', 'user__username', 'user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['created_at', 'grand_total', 'status']
    ordering = ['-created_at']
    filter_fields = ('status', 'payment_method', 'payment_status', 'user')

    def get_serializer_class(self):
        return s.AdminOrderListSerializer if self.action == 'list' else s.AdminOrderSerializer

    def perform_update(self, serializer):
        order = serializer.instance
        new_status = serializer.validated_data.get('status', order.status)
        if new_status == 'cancelled' and order.status != 'cancelled':
            # Cancelling restocks and refunds a paid online payment.
            try:
                order_services.cancel(order)
            except (order_services.CheckoutError, rzp.RazorpayError) as exc:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'detail': f'Could not cancel: refund failed ({exc}).'})
            serializer.validated_data.pop('status')
        if new_status == 'delivered' and order.payment_method == 'cod' and 'payment_status' not in serializer.validated_data:
            # Cash is collected on delivery.
            serializer.validated_data['payment_status'] = 'paid'
        instance = serializer.save()
        if instance.payment_status == 'paid' and not instance.paid_at:
            from django.utils import timezone
            instance.paid_at = timezone.now()
            instance.save(update_fields=['paid_at', 'updated_at'])

    def create(self, request, *args, **kwargs):
        # Orders are only created by customers at checkout.
        return Response({'detail': 'Method "POST" not allowed.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=['post'])
    def refund(self, request, order_number=None):
        """POST /api/admin/orders/<order_number>/refund/ — full refund of a
        paid online order through Razorpay (the order itself stays as is;
        cancel it too if it won't ship)."""
        order = self.get_object()
        try:
            order_services.refund(order, reason=str(request.data.get('reason', ''))[:200])
        except (order_services.CheckoutError, rzp.RazorpayError) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(s.AdminOrderSerializer(self.get_queryset().get(pk=order.pk), context={'request': request}).data)

    def get_queryset(self):
        qs = super().get_queryset()
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs


class CustomerViewSet(AdminViewSet):
    http_method_names = ['get', 'patch', 'head', 'options']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'last_login', 'order_count', 'total_spent']
    ordering = ['-date_joined']
    filter_fields = ('is_active', 'is_staff')

    def get_queryset(self):
        self.queryset = s.customer_totals(User.objects.all())
        return super().get_queryset()

    def get_serializer_class(self):
        return s.AdminCustomerDetailSerializer if self.action == 'retrieve' else s.AdminCustomerSerializer

    def perform_update(self, serializer):
        user = serializer.instance
        if user == self.request.user and (
            serializer.validated_data.get('is_active') is False
            or serializer.validated_data.get('is_staff') is False
        ):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': "You can't deactivate or remove admin access from your own account."})
        serializer.save()


class CouponViewSet(AdminViewSet):
    queryset = Coupon.objects.all()
    serializer_class = s.AdminCouponSerializer
    search_fields = ['code']
    ordering_fields = ['created_at', 'code', 'times_used']
    ordering = ['-created_at']
    filter_fields = ('is_active', 'discount_type')


# --- Website content ---------------------------------------------------------

class BannerViewSet(AdminViewSet):
    queryset = Banner.objects.all()
    serializer_class = s.AdminBannerSerializer
    search_fields = ['title', 'subtitle']
    ordering = ['display_order', 'id']
    filter_fields = ('is_active',)


class TestimonialViewSet(AdminViewSet):
    queryset = Testimonial.objects.all()
    serializer_class = s.AdminTestimonialSerializer
    search_fields = ['author_name', 'quote']
    ordering = ['-id']
    filter_fields = ('is_active',)


class InstagramPostViewSet(AdminViewSet):
    queryset = InstagramPost.objects.all()
    serializer_class = s.AdminInstagramPostSerializer
    ordering = ['display_order', 'id']
    filter_fields = ('is_active',)


class BlogPostViewSet(AdminViewSet):
    queryset = BlogPost.objects.all()
    serializer_class = s.AdminBlogPostSerializer
    search_fields = ['title', 'excerpt', 'author_name']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']
    filter_fields = ('is_published',)


class FAQViewSet(AdminViewSet):
    queryset = FAQ.objects.all()
    serializer_class = s.AdminFAQSerializer
    search_fields = ['question', 'answer']
    ordering = ['display_order', 'id']
    filter_fields = ('is_active',)


class ContactMessageViewSet(AdminViewSet):
    queryset = ContactMessage.objects.all()
    serializer_class = s.AdminContactMessageSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
    search_fields = ['name', 'email', 'subject', 'message']
    ordering = ['-created_at']
    filter_fields = ('is_read',)


class NewsletterSubscriberViewSet(
    mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsStaff]
    pagination_class = AdminPagination
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = s.AdminNewsletterSubscriberSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email']
    ordering = ['-subscribed_at']

    @action(detail=False, methods=['get'])
    def export(self, request):
        """CSV download of every subscriber email."""
        from django.http import HttpResponse

        rows = ['email,subscribed_at'] + [
            f'{sub.email},{sub.subscribed_at.isoformat()}' for sub in self.get_queryset()
        ]
        response = HttpResponse('\n'.join(rows), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="subscribers.csv"'
        return response


class SiteSettingsAPIView(APIView):
    """GET/PATCH /api/admin/site-settings/ — the single SiteSettings row."""

    permission_classes = [IsStaff]

    def _instance(self):
        return SiteSettings.objects.first() or SiteSettings.objects.create()

    def get(self, request):
        return Response(s.AdminSiteSettingsSerializer(self._instance()).data)

    def patch(self, request):
        serializer = s.AdminSiteSettingsSerializer(self._instance(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
