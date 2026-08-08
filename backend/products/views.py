from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from categories.models import Category, Collection

from .models import Product, ProductReview, RecentlyViewed


def _base_queryset():
    return Product.objects.filter(status='published').prefetch_related('images', 'variants')


def shop_view(request):
    products = _base_queryset()

    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)

    color = request.GET.get('color')
    if color:
        products = products.filter(color__iexact=color)

    size = request.GET.get('size')
    if size:
        products = products.filter(variants__size=size, variants__stock_quantity__gt=0).distinct()

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(sku__icontains=query)
        )

    sort = request.GET.get('sort', 'newest')
    sort_map = {
        'newest': '-created_at',
        'price_low': 'price',
        'price_high': '-price',
        'name': 'name',
    }
    products = products.order_by(sort_map.get(sort, '-created_at'))

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'categories': Category.objects.filter(is_active=True),
        'colors': Product.objects.filter(status='published').exclude(color='').values_list(
            'color', flat=True).distinct(),
        'current_category': category_slug,
        'current_sort': sort,
        'query': query or '',
    }
    return render(request, 'products/shop.html', context)


def shop_by_category(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = _base_queryset().filter(category=category).order_by('-created_at')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'products/shop.html', {
        'page_obj': page_obj,
        'categories': Category.objects.filter(is_active=True),
        'current_category': slug,
        'category_obj': category,
    })


def shop_by_collection(request, slug):
    collection = get_object_or_404(Collection, slug=slug, is_active=True)
    products = _base_queryset().filter(collections=collection).order_by('-created_at')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'products/shop.html', {
        'page_obj': page_obj,
        'categories': Category.objects.filter(is_active=True),
        'collection_obj': collection,
    })


def product_detail(request, slug):
    product = get_object_or_404(_base_queryset(), slug=slug)

    if not request.session.session_key:
        request.session.save()
    RecentlyViewed.objects.update_or_create(
        session_key=request.session.session_key, product=product
    )

    related = _base_queryset().filter(category=product.category).exclude(pk=product.pk)[:4]

    recently_viewed_ids = RecentlyViewed.objects.filter(
        session_key=request.session.session_key
    ).exclude(product=product).order_by('-viewed_at').values_list('product_id', flat=True)[:4]
    recently_viewed = Product.objects.filter(id__in=list(recently_viewed_ids))

    # Rule-based "complete the look": other published products from a different category.
    complete_the_look = _base_queryset().exclude(
        category=product.category
    ).exclude(pk=product.pk).order_by('?')[:4]

    reviews = product.reviews.filter(is_approved=True)

    context = {
        'product': product,
        'related_products': related,
        'recently_viewed': recently_viewed,
        'complete_the_look': complete_the_look,
        'reviews': reviews,
    }
    return render(request, 'products/product_detail.html', context)


@login_required
def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug)
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 5))
        title = request.POST.get('title', '')
        comment = request.POST.get('comment', '')
        ProductReview.objects.update_or_create(
            product=product, user=request.user,
            defaults={'rating': rating, 'title': title, 'comment': comment},
        )
        messages.success(request, 'Thank you for your review.')
    return redirect('products:product_detail', slug=slug)


def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    results = []
    if len(query) >= 2:
        products = Product.objects.filter(
            status='published', name__icontains=query
        ).values('name', 'slug')[:8]
        results = list(products)
    return JsonResponse({'results': results})
