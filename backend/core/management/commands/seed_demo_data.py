import io
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from categories.models import Category, Collection
from orders.models import Coupon
from products.models import Product, ProductImage, ProductVariant
from website.models import FAQ, Banner, BlogPost, InstagramPost, SiteSettings, Testimonial


def _placeholder_image(text, size=(900, 1125), bg=(17, 17, 17)):
    """A plain solid-color JPEG, generated on the fly with Pillow (already
    a dependency) — there's no real product photography in this repo (see
    README), so seeded content gets *something* real to display instead
    of nothing. The frontend still falls back to placehold.co for any
    image that's genuinely absent (e.g. content added via /admin/ without
    a photo)."""
    from PIL import Image as PILImage

    img = PILImage.new('RGB', size, color=bg)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=70)
    return ContentFile(buf.getvalue(), name=f'{slugify(text)[:40]}.jpg')


class Command(BaseCommand):
    help = 'Seed the database with demo categories, products, testimonials, FAQs, coupons and content.'

    def handle(self, *args, **options):
        cats = [
            ('Outerwear', 'Precision-tailored coats and jackets.'),
            ('Knitwear', 'Luxury fibers, minimal silhouettes.'),
            ('Tailoring', 'Structured suiting for the modern wardrobe.'),
            ('Denim', 'Raw, sculpted, and built to last.'),
        ]
        cat_objs = {}
        for name, desc in cats:
            c, _ = Category.objects.get_or_create(name=name, defaults={'description': desc})
            if not c.image:
                c.image.save(f'{c.slug}.jpg', _placeholder_image(name), save=True)
            cat_objs[name] = c

        collection, _ = Collection.objects.get_or_create(
            name='Autumn Drop 01',
            defaults={'description': 'Limited autumn release.', 'is_limited_drop': True},
        )

        products_data = [
            ('Onyx Wool Overcoat', 'Outerwear', 'FX-OWC-001', 18999, 22999, 'Charcoal', True, True, False, False),
            ('Cashmere Crew Sweater', 'Knitwear', 'FX-CCS-002', 9499, None, 'Ivory', True, False, True, False),
            ('Structured Wool Blazer', 'Tailoring', 'FX-SWB-003', 15999, 17999, 'Black', False, True, False, True),
            ('Sculpted Raw Denim', 'Denim', 'FX-SRD-004', 7999, None, 'Indigo', True, False, True, False),
            ('Silk-Blend Trench', 'Outerwear', 'FX-SBT-005', 21999, None, 'Sand', False, True, False, False),
            ('Merino Turtleneck', 'Knitwear', 'FX-MTN-006', 8499, 9999, 'Black', False, False, True, True),
            ('Tapered Wool Trouser', 'Tailoring', 'FX-TWT-007', 10999, None, 'Graphite', True, False, False, True),
            ('Selvedge Denim Jacket', 'Denim', 'FX-SDJ-008', 12999, 14999, 'Washed Blue', False, True, True, False),
        ]

        created_count = 0
        for name, cat, sku, price, compare, color, feat, trend, new, best in products_data:
            product, created = Product.objects.get_or_create(
                name=name,
                defaults=dict(
                    sku=sku,
                    category=cat_objs[cat],
                    short_description=f'{name} — engineered for permanence.',
                    description=(
                        f'The {name} is crafted from premium materials in a limited run, designed for '
                        'those who value restraint over noise. Every seam is finished by hand.'
                    ),
                    fabric_details='Fabric composition: premium natural fibers. Dry clean only.',
                    size_guide='True to size. Consult our size chart for a tailored fit.',
                    price=Decimal(str(price)),
                    compare_at_price=Decimal(str(compare)) if compare else None,
                    color=color,
                    available_sizes='S,M,L,XL',
                    is_featured=feat, is_trending=trend, is_new_arrival=new, is_best_seller=best,
                    status='published',
                ),
            )
            if created:
                created_count += 1
                product.collections.add(collection)
                for size in ['S', 'M', 'L', 'XL']:
                    ProductVariant.objects.create(product=product, size=size, stock_quantity=12)
                primary = ProductImage(product=product, is_primary=True, display_order=0)
                primary.image.save(f'{product.slug}-1.jpg', _placeholder_image(name), save=True)
                secondary = ProductImage(product=product, is_primary=False, display_order=1)
                secondary.image.save(f'{product.slug}-2.jpg', _placeholder_image(f'{name} alt', bg=(30, 27, 24)), save=True)

        testimonials = [
            ('Ananya R.', 'Creative Director', 'FEXO understands restraint. Every piece feels considered, not manufactured.'),
            ('Karan V.', 'Architect', 'The tailoring is unlike anything else at this price point. Genuinely investment pieces.'),
            ('Meera S.', 'Editor', "I've replaced half my wardrobe with FEXO. The fabric quality alone justifies it."),
        ]
        for name, title, quote in testimonials:
            Testimonial.objects.get_or_create(author_name=name, defaults={'author_title': title, 'quote': quote})

        faqs = [
            ('What is your return policy?', 'We accept returns within 14 days of delivery for unworn items with tags attached.'),
            ('Do you ship internationally?', 'Currently FEXO ships within India only. International shipping is coming soon.'),
            ('How do I find my size?', 'Refer to the size guide on each product page, or contact our styling team for a personal recommendation.'),
            ('Is Cash on Delivery available?', 'Yes, all FEXO orders currently ship with Cash on Delivery as the payment method.'),
        ]
        for q, a in faqs:
            FAQ.objects.get_or_create(question=q, defaults={'answer': a})

        coupons = [
            ('FEXO10', 'percent', Decimal('10.00'), Decimal('2000.00')),
            ('FLAT500', 'flat', Decimal('500.00'), Decimal('5000.00')),
        ]
        for code, discount_type, value, minimum in coupons:
            Coupon.objects.get_or_create(
                code=code,
                defaults={'discount_type': discount_type, 'discount_value': value, 'minimum_order_value': minimum},
            )

        blog_posts = [
            ('The Case for Fewer, Better Things', 'Why we release four collections a year instead of fifty-two.',
             'Fast fashion optimizes for now. We optimize for the next decade — fewer ateliers, better '
             'fabric, and pieces built to be repaired rather than replaced.'),
            ('Inside the Atelier: Wool Sourcing', 'A look at the small mill that supplies every coat in the Autumn Drop.',
             'We visit twice a year, choose the lots by hand, and commit to volumes months in advance so the '
             'mill can plan around us rather than the other way around.'),
            ('How to Actually Care for Merino Wool', 'You are probably washing your sweaters too often.',
             'Air it out before you wash it. Hand wash cold when you do, lay flat to dry, and store folded, never hung.'),
        ]
        for title, excerpt, content in blog_posts:
            post, _ = BlogPost.objects.get_or_create(title=title, defaults={'excerpt': excerpt, 'content': content})
            if not post.cover_image:
                post.cover_image.save(f'{post.slug}.jpg', _placeholder_image(title, size=(1200, 700)), save=True)

        if InstagramPost.objects.count() < 6:
            for i in range(6 - InstagramPost.objects.count()):
                ip = InstagramPost(display_order=i)
                ip.image.save(f'instagram-{i}.jpg', _placeholder_image(f'fexo {i}', size=(600, 600)), save=True)

        if not Banner.objects.exists():
            banner = Banner(title='Autumn Collection', subtitle='Live in Fashion', link_url='/shop')
            banner.image.save('hero.jpg', _placeholder_image('FEXO Hero', size=(1600, 900), bg=(10, 10, 10)), save=True)

        if not SiteSettings.objects.exists():
            SiteSettings.objects.create(
                site_name='FEXO',
                tagline='Live in Fashion',
                contact_email='hello@fexo.com',
            )

        self.stdout.write(self.style.SUCCESS(
            f'Seed complete. {created_count} new products created. Total products: {Product.objects.count()}'
        ))
