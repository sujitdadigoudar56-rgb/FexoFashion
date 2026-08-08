from decimal import Decimal

from django.core.management.base import BaseCommand

from categories.models import Category, Collection
from products.models import Product, ProductVariant
from website.models import FAQ, SiteSettings, Testimonial


class Command(BaseCommand):
    help = "Seed the database with demo categories, products, testimonials and FAQs."

    def handle(self, *args, **options):
        cats = [
            ("Outerwear", "Precision-tailored coats and jackets."),
            ("Knitwear", "Luxury fibers, minimal silhouettes."),
            ("Tailoring", "Structured suiting for the modern wardrobe."),
            ("Denim", "Raw, sculpted, and built to last."),
        ]
        cat_objs = {}
        for name, desc in cats:
            c, _ = Category.objects.get_or_create(name=name, defaults={"description": desc})
            cat_objs[name] = c

        collection, _ = Collection.objects.get_or_create(
            name="Autumn Drop 01",
            defaults={"description": "Limited autumn release.", "is_limited_drop": True},
        )

        products_data = [
            ("Onyx Wool Overcoat", "Outerwear", "FX-OWC-001", 18999, 22999, "Charcoal", True, True, False, False),
            ("Cashmere Crew Sweater", "Knitwear", "FX-CCS-002", 9499, None, "Ivory", True, False, True, False),
            ("Structured Wool Blazer", "Tailoring", "FX-SWB-003", 15999, 17999, "Black", False, True, False, True),
            ("Sculpted Raw Denim", "Denim", "FX-SRD-004", 7999, None, "Indigo", True, False, True, False),
            ("Silk-Blend Trench", "Outerwear", "FX-SBT-005", 21999, None, "Sand", False, True, False, False),
            ("Merino Turtleneck", "Knitwear", "FX-MTN-006", 8499, 9999, "Black", False, False, True, True),
            ("Tapered Wool Trouser", "Tailoring", "FX-TWT-007", 10999, None, "Graphite", True, False, False, True),
            ("Selvedge Denim Jacket", "Denim", "FX-SDJ-008", 12999, 14999, "Washed Blue", False, True, True, False),
        ]

        created_count = 0
        for name, cat, sku, price, compare, color, feat, trend, new, best in products_data:
            product, created = Product.objects.get_or_create(
                name=name,
                defaults=dict(
                    sku=sku,
                    category=cat_objs[cat],
                    short_description=f"{name} \u2014 engineered for permanence.",
                    description=(
                        f"The {name} is crafted from premium materials in a limited run, designed for "
                        "those who value restraint over noise. Every seam is finished by hand."
                    ),
                    fabric_details="Fabric composition: premium natural fibers. Dry clean only.",
                    size_guide="True to size. Consult our size chart for a tailored fit.",
                    price=Decimal(str(price)),
                    compare_at_price=Decimal(str(compare)) if compare else None,
                    color=color,
                    available_sizes="S,M,L,XL",
                    is_featured=feat, is_trending=trend, is_new_arrival=new, is_best_seller=best,
                    status="published",
                ),
            )
            if created:
                created_count += 1
                product.collections.add(collection)
                for size in ["S", "M", "L", "XL"]:
                    ProductVariant.objects.create(product=product, size=size, stock_quantity=12)

        testimonials = [
            ("Ananya R.", "Creative Director", "FEXO understands restraint. Every piece feels considered, not manufactured."),
            ("Karan V.", "Architect", "The tailoring is unlike anything else at this price point. Genuinely investment pieces."),
            ("Meera S.", "Editor", "I've replaced half my wardrobe with FEXO. The fabric quality alone justifies it."),
        ]
        for name, title, quote in testimonials:
            Testimonial.objects.get_or_create(author_name=name, defaults={"author_title": title, "quote": quote})

        faqs = [
            ("What is your return policy?", "We accept returns within 14 days of delivery for unworn items with tags attached."),
            ("Do you ship internationally?", "Currently FEXO ships within India only. International shipping is coming soon."),
            ("How do I find my size?", "Refer to the size guide on each product page, or contact our styling team for a personal recommendation."),
            ("Is Cash on Delivery available?", "Yes, all FEXO orders currently ship with Cash on Delivery as the payment method."),
        ]
        for q, a in faqs:
            FAQ.objects.get_or_create(question=q, defaults={"answer": a})

        if not SiteSettings.objects.exists():
            SiteSettings.objects.create(
                site_name="FEXO",
                tagline="Live in Fashion",
                contact_email="hello@fexo.com",
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete. {created_count} new products created. Total products: {Product.objects.count()}"
        ))
        self.stdout.write(self.style.WARNING(
            "Note: demo products have no images attached. Upload images per product via /admin/ for full visuals."
        ))
