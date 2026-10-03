from django.db.models import Avg, Count, ExpressionWrapper, DecimalField, F, Q
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