from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product, ProductReview
from .serializers import ProductReviewSerializer, ProductSerializer


def _base_queryset():
    return Product.objects.filter(status='published').select_related('category').prefetch_related(
        'images', 'variants', 'collections', 'reviews'
    )


class ProductListAPIView(generics.ListAPIView):
    """GET /api/products/ — same filters/sort the old shop_view supported
    (category, collection, color, size, min_price, max_price, q, sort),
    plus page/page_size via DRF's PageNumberPagination (PAGE_SIZE=12,
    matching the original Paginator(products, 12)).

    `sort=random` is new — the frontend uses it to power "Complete the
    Look" (the original view did `.order_by('?')` server-side for that;
    there's no dedicated endpoint for it, the frontend just filters this
    list client-side by category/self, same as it already does for
    "related products").
    """

    serializer_class = ProductSerializer

    def get_queryset(self):
        products = _base_queryset()
        params = self.request.query_params

        category = params.get('category')
        if category:
            products = products.filter(category__slug=category)

        collection = params.get('collection')
        if collection:
            products = products.filter(collections__slug=collection)

        color = params.get('color')
        if color:
            products = products.filter(color__iexact=color)

        size = params.get('size')
        if size:
            products = products.filter(variants__size=size, variants__stock_quantity__gt=0)

        min_price = params.get('min_price')
        if min_price:
            products = products.filter(price__gte=min_price)

        max_price = params.get('max_price')
        if max_price:
            products = products.filter(price__lte=max_price)

        query = params.get('q')
        if query:
            products = products.filter(
                Q(name__icontains=query) | Q(description__icontains=query) | Q(sku__icontains=query)
            )

        # Boolean flag filters — power the home page's Featured/Trending/
        # New Arrivals/Best Sellers rails (each is just this list endpoint
        # with one of these set to true).
        for flag in ('is_featured', 'is_trending', 'is_new_arrival', 'is_best_seller'):
            if params.get(flag) == 'true':
                products = products.filter(**{flag: True})

        sort = params.get('sort', 'newest')
        if sort == 'random':
            return products.distinct().order_by('?')

        sort_map = {
            'newest': '-created_at',
            'price_low': 'price',
            'price_high': '-price',
            'name': 'name',
            'popularity':'OrderItem',
            'rating': '-reviews__rating',
            'discount': 'compare_at_price - price',
        }
        return products.distinct().order_by(sort_map.get(sort, '-created_at'))


class ProductDetailAPIView(generics.RetrieveAPIView):
    """GET /api/products/<slug>/ — nested images/variants/category/
    collections/reviews. (Session-based RecentlyViewed tracking from the
    original view isn't ported — the frontend already tracks that
    client-side in localStorage, which needs no backend support.)"""

    serializer_class = ProductSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return _base_queryset()


class AddReviewAPIView(APIView):
    """POST /api/products/<slug>/review/ — one review per (product, user),
    same as the original add_review view's update_or_create."""

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
    """GET /api/products/search-suggestions/?q= — lightweight name/slug
    pairs for the nav search overlay, same shape the original view
    returned."""

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        results = []
        if len(query) >= 2:
            results = list(
                Product.objects.filter(status='published')
                .filter(Q(name__icontains=query) | Q(category__name__icontains=query) | Q(description__icontains=query))
                .distinct()
                .values('name', 'slug')[:8]
            )
        return Response({'results': results})
