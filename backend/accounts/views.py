from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from orders.models import Order
from wishlist.models import WishlistItem

from .forms import AddressForm, ProfileForm, RegisterForm
from .models import Address, Profile


class FexoLoginView(LoginView):
    template_name = 'accounts/login.html'


class FexoPasswordResetView(PasswordResetView):
    template_name = 'accounts/forgot_password.html'
    email_template_name = 'accounts/password_reset_email.html'
    success_url = reverse_lazy('accounts:password_reset_done')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('website:home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Welcome to FEXO. Your account has been created.')
            return redirect('website:home')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard_view(request):
    orders = Order.objects.filter(user=request.user)[:5]
    wishlist_count = WishlistItem.objects.filter(wishlist__user=request.user).count()
    addresses = Address.objects.filter(user=request.user)
    context = {
        'orders': orders,
        'order_count': Order.objects.filter(user=request.user).count(),
        'wishlist_count': wishlist_count,
        'addresses': addresses,
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            messages.success(request, 'Profile updated.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(
            instance=profile,
            initial={
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            },
        )
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def orders_view(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'accounts/orders.html', {'orders': orders})


@login_required
def addresses_view(request):
    addresses = Address.objects.filter(user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            if address.is_default:
                Address.objects.filter(user=request.user).update(is_default=False)
            address.save()
            messages.success(request, 'Address saved.')
            return redirect('accounts:addresses')
    else:
        form = AddressForm()
    return render(request, 'accounts/addresses.html', {'addresses': addresses, 'form': form})


@login_required
def delete_address_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.delete()
    messages.success(request, 'Address removed.')
    return redirect('accounts:addresses')
