from django.db.models import Avg, Count, ExpressionWrapper, DecimalField, F, Max, Min, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product, ProductReview
from .serializers import ProductReviewSerializer, ProductSerializer


def _base_queryset():
    # Approved reviews are prefetched once (ProductSerializer reads them from
    # this prefetch) instead of one extra query per product.
    return Product.objects.filter(status='published').select_related('category').prefetch_related(
        'images', 'variants', 'collections',
        Prefetch('reviews', queryset=ProductReview.objects.filter(is_approved=True).select_related('user'),
                 to_attr='approved_reviews'),
    )


def _csv(params, key):
    """Comma-separated (or repeated) query param -> list of non-empty values."""
    values = []
    for raw in params.getlist(key):
        values.extend(v.strip() for v in raw.split(',') if v.strip())
    return values


class ProductPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 48


class ProductListAPIView(generics.ListAPIView):
    """GET /api/products/ — filters accept comma-separated values:
    category, size, color, price (bands like `0-1000,1500-`), plus
    collection, min_price/max_price, in_stock=true, q, and sort."""

    serializer_class = ProductSerializer
    pagination_class = ProductPagination

    def get_queryset(self):
        products = _base_queryset()
        params = self.request.query_params

        categories = _csv(params, 'category')
        if categories:
            products = products.filter(Q(category__slug__in=categories) | Q(category__parent__slug__in=categories))

        collection = params.get('collection')
        if collection:
            products = products.filter(collections__slug=collection)

        colors = _csv(params, 'color')
        if colors:
            color_q = Q()
            for color in colors:
                color_q |= Q(color__iexact=color)
            products = products.filter(color_q)

        sizes = _csv(params, 'size')
        if sizes:
            products = products.filter(variants__size__in=sizes, variants__stock_quantity__gt=0)

        bands = _csv(params, 'price')
        if bands:
            band_q = Q()
            for band in bands:
                low, _, high = band.partition('-')
                cond = Q()
                if low.strip().isdigit():
                    cond &= Q(price__gte=int(low))
                if high.strip().isdigit():
                    cond &= Q(price__lte=int(high))
                band_q |= cond
            products = products.filter(band_q)

        if params.get('in_stock') == 'true':
            products = products.filter(variants__stock_quantity__gt=0)

        min_price = params.get('min_price')
        if min_price:
            products = products.filter(price__gte=min_price)

        max_price = params.get('max_price')
        if max_price:
            products = products.filter(price__lte=max_price)

        query = params.get('q')
        if query:
            products = products.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(sku__icontains=query)
                | Q(category__name__icontains=query)
            )

        for flag in ('is_featured', 'is_trending', 'is_new_arrival', 'is_best_seller'):
            if params.get(flag) == 'true':
                products = products.filter(**{flag: True})

        sort = params.get('sort', 'newest')
        if sort == 'random':
            return products.distinct().order_by('?')

        if sort == 'popularity':
            products = products.annotate(
                _popularity=Count(
                    'orderitem',
                    filter=~Q(orderitem__order__status='cancelled'),
                    distinct=True,
                )
            )
            return products.distinct().order_by('-_popularity', '-created_at')

        if sort == 'rating':
            products = products.annotate(
                _avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True))
            )
            return products.distinct().order_by(F('_avg_rating').desc(nulls_last=True), '-created_at')

        if sort in ('discount_low', 'discount_high'):
            products = products.annotate(
                _discount=ExpressionWrapper(
                    F('compare_at_price') - F('price'), output_field=DecimalField()
                )
            )
            direction = (
                F('_discount').asc(nulls_last=True)
                if sort == 'discount_low'
                else F('_discount').desc(nulls_last=True)
            )
            return products.distinct().order_by(direction)

        sort_map = {
            'relevance': '-is_featured',
            'newest': '-created_at',
            'price_low': 'price',
            'price_high': '-price',
            'name': 'name',
        }
        return products.distinct().order_by(sort_map.get(sort, '-created_at'))


class ProductDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return _base_queryset()


class AddReviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        try:
            rating = int(request.data.get('rating', 5))
        except (TypeError, ValueError):
            rating = 5
        review, _ = ProductReview.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={
                'rating': rating,
                'title': request.data.get('title', ''),
                'comment': request.data.get('comment', ''),
            },
        )
        serializer = ProductReviewSerializer(review, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SearchSuggestionsAPIView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        results = []
        if len(query) >= 2:
            results = list(
                Product.objects.filter(status='published')
                .filter(
                    Q(name__icontains=query)
                    | Q(category__name__icontains=query)
                    | Q(description__icontains=query)
                )
                .distinct()
                .values('name', 'slug')[:8]
            )
        return Response({'results': results})


class ProductFacetsAPIView(APIView):
    """GET /api/products/facets/ — the options the shop filter sidebar
    offers: categories (with product counts), colours, sizes and the price
    range of published products."""

    def get(self, request):
        published = Product.objects.filter(status='published')
        categories = (
            published.values('category__name', 'category__slug')
            .annotate(count=Count('id'))
            .order_by('category__name')
        )
        colors = sorted({c.strip().title() for c in published.values_list('color', flat=True) if c and c.strip()})
        size_order = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
        sizes = set()
        for value in published.values_list('available_sizes', flat=True):
            sizes.update(s.strip() for s in (value or '').split(',') if s.strip())
        price = published.aggregate(min=Min('price'), max=Max('price'))
        return Response({
            'categories': [
                {'name': c['category__name'], 'slug': c['category__slug'], 'count': c['count']}
                for c in categories
            ],
            'colors': colors,
            'sizes': [s for s in size_order if s in sizes] + sorted(sizes - set(size_order)),
            'price_min': float(price['min'] or 0),
            'price_max': float(price['max'] or 0),
        })
