from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Address
from cart.utils import get_cart
from products.models import ProductVariant

from .models import Order, OrderItem


@login_required
def checkout_view(request):
    cart = get_cart(request)
    if not cart or cart.items.count() == 0:
        messages.warning(request, 'Your bag is empty.')
        return redirect('cart:cart_detail')

    addresses = Address.objects.filter(user=request.user)

    if request.method == 'POST':
        billing_id = request.POST.get('billing_address')
        shipping_id = request.POST.get('shipping_address')
        billing = get_object_or_404(Address, pk=billing_id, user=request.user)
        shipping = get_object_or_404(Address, pk=shipping_id, user=request.user)

        order = Order.objects.create(
            user=request.user,
            billing_address=billing,
            shipping_address=shipping,
            subtotal=cart.subtotal,
            gst_amount=cart.gst_total,
            shipping_cost=cart.shipping_cost,
            discount_amount=cart.discount_amount,
            grand_total=cart.grand_total,
            coupon=cart.coupon,
            payment_method='cod',
            notes=request.POST.get('notes', ''),
        )

        for item in cart.items.select_related('product', 'variant'):
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                unit_price=item.product.price,
                quantity=item.quantity,
                size=item.variant.size if item.variant else '',
            )
            if item.variant:
                variant = ProductVariant.objects.select_for_update().get(pk=item.variant.pk)
                variant.stock_quantity = max(0, variant.stock_quantity - item.quantity)
                variant.save()

        if order.coupon:
            order.coupon.times_used += 1
            order.coupon.save()

        cart.items.all().delete()
        cart.coupon = None
        cart.save()

        return redirect('orders:order_success', order_number=order.order_number)

    return render(request, 'orders/checkout.html', {'cart': cart, 'addresses': addresses})


@login_required
def order_success_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/order_success.html', {'order': order})


@login_required
def order_detail_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})
