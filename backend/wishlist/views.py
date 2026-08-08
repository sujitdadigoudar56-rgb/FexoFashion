from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from products.models import Product

from .models import Wishlist, WishlistItem


@login_required
def wishlist_view(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    return render(request, 'wishlist/wishlist.html', {'wishlist': wishlist})


@login_required
@require_POST
def wishlist_toggle(request, slug):
    product = get_object_or_404(Product, slug=slug)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
    if not created:
        item.delete()
        messages.info(request, 'Removed from wishlist.')
    else:
        messages.success(request, 'Added to wishlist.')
    return redirect(request.POST.get('next') or 'wishlist:wishlist')
