from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from categories.models import Category, Collection
from products.models import Product

from .forms import ContactForm, NewsletterForm
from .models import Banner, BlogPost, FAQ, InstagramPost, Testimonial


def home_view(request):
    context = {
        'banners': Banner.objects.filter(is_active=True),
        'featured_products': Product.objects.filter(status='published', is_featured=True)[:8],
        'trending_products': Product.objects.filter(status='published', is_trending=True)[:8],
        'new_arrivals': Product.objects.filter(status='published', is_new_arrival=True)[:8],
        'best_sellers': Product.objects.filter(status='published', is_best_seller=True)[:8],
        'limited_drops': Collection.objects.filter(is_active=True, is_limited_drop=True)[:3],
        'testimonials': Testimonial.objects.filter(is_active=True),
        'instagram_posts': InstagramPost.objects.filter(is_active=True)[:8],
        'categories': Category.objects.filter(is_active=True, parent__isnull=True)[:6],
        'newsletter_form': NewsletterForm(),
    }
    return render(request, 'website/home.html', context)


def about_view(request):
    return render(request, 'website/about.html')


def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Message sent. We'll be in touch shortly.")
            return redirect('website:contact')
    else:
        form = ContactForm()
    return render(request, 'website/contact.html', {'form': form})


def faq_view(request):
    return render(request, 'website/faq.html', {'faqs': FAQ.objects.filter(is_active=True)})


def journal_view(request):
    posts = BlogPost.objects.filter(is_published=True)
    return render(request, 'website/journal.html', {'posts': posts})


def journal_detail_view(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    return render(request, 'website/journal_detail.html', {'post': post})


def static_page(template_name):
    def view(request):
        return render(request, f'website/{template_name}.html')
    return view


privacy_policy_view = static_page('privacy_policy')
terms_view = static_page('terms')
shipping_view = static_page('shipping')
returns_view = static_page('returns')


def newsletter_signup(request):
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subscribed! Welcome to the FEXO inner circle.')
        else:
            messages.error(request, 'Please enter a valid email.')
    return redirect(request.POST.get('next') or 'website:home')
