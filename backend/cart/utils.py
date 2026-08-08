from .models import Cart


def get_cart(request, create=True):
    """Fetch the cart for the current user/session, merging session cart into user cart on login."""
    if not request.session.session_key:
        request.session.save()

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart is None and create:
            cart = Cart.objects.create(user=request.user)

        # Merge any anonymous session cart into the user's cart.
        session_cart = Cart.objects.filter(
            session_key=request.session.session_key, user__isnull=True
        ).first()
        if session_cart and cart:
            for item in session_cart.items.all():
                existing = cart.items.filter(product=item.product, variant=item.variant).first()
                if existing:
                    existing.quantity += item.quantity
                    existing.save()
                else:
                    item.cart = cart
                    item.save()
            session_cart.delete()
        return cart

    cart = Cart.objects.filter(session_key=request.session.session_key, user__isnull=True).first()
    if cart is None and create:
        cart = Cart.objects.create(session_key=request.session.session_key)
    return cart
