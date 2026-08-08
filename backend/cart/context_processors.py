from .utils import get_cart


def cart_summary(request):
    cart = get_cart(request, create=False)
    return {'cart_item_count': cart.item_count if cart else 0}
