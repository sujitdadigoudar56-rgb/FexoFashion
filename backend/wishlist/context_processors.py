def wishlist_summary(request):
    if request.user.is_authenticated:
        from .models import Wishlist
        wishlist = Wishlist.objects.filter(user=request.user).first()
        return {'wishlist_count': wishlist.items.count() if wishlist else 0}
    return {'wishlist_count': 0}
