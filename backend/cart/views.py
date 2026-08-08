from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders.models import Coupon
from products.models import Product, ProductVariant

from .models import CartItem
from .utils import get_cart


def cart_detail(request):
    cart = get_cart(request)
    return render(request, 'cart/cart.html', {'cart': cart})


@require_POST
def cart_add(request, slug):
    product = get_object_or_404(Product, slug=slug, status='published')
    cart = get_cart(request)
    variant_id = request.POST.get('variant')
    quantity = int(request.POST.get('quantity', 1) or 1)
    variant = ProductVariant.objects.filter(pk=variant_id, product=product).first() if variant_id else None

    item, created = CartItem.objects.get_or_create(cart=cart, product=product, variant=variant)
    if not created:
        item.quantity += quantity
    else:
        item.quantity = quantity
    item.save()
    messages.success(request, f'{product.name} added to your bag.')
    return redirect(request.POST.get('next') or 'cart:cart_detail')


@require_POST
def cart_update(request, item_id):
    cart = get_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    quantity = int(request.POST.get('quantity', 1) or 1)
    if quantity <= 0:
        item.delete()
    else:
        item.quantity = quantity
        item.save()
    return redirect('cart:cart_detail')


@require_POST
def cart_remove(request, item_id):
    cart = get_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()
    messages.info(request, 'Item removed from bag.')
    return redirect('cart:cart_detail')


@require_POST
def apply_coupon(request):
    cart = get_cart(request)
    code = request.POST.get('code', '').strip().upper()
    coupon = Coupon.objects.filter(code=code).first()
    if coupon and coupon.is_valid:
        cart.coupon = coupon
        cart.save()
        messages.success(request, f'Coupon "{code}" applied.')
    else:
        messages.error(request, 'That coupon is invalid or expired.')
    return redirect('cart:cart_detail')
