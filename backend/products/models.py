from decimal import Decimal
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from categories.models import Category, Collection

SIZE_CHOICES = [
    ('XS', 'XS'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL'),
]
COLORS = [
    'Gray', 'Navy Blue', 'Black', 'Brown', 'Charcoal', 'White',
    'Beige', 'Maroon', 'Cement Gray', 'Cream', 'Olive Green',
]
COLOR_CHOICES = [(c, c) for c in COLORS]


class Product(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    sku = models.CharField(max_length=40, unique=True)

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    collections = models.ManyToManyField(Collection, blank=True, related_name='products')

    short_description = models.CharField(max_length=300, blank=True)
    description = models.TextField()
    fabric_details = models.TextField(blank=True)
    size_guide = models.TextField(blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gst_percent = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('5.00'))

    available_sizes = models.CharField(
        max_length=60, blank=True,
        help_text='Comma separated, e.g. S,M,L,XL'
    )

    is_featured = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='published')

    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'is_featured'])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f'{base}-{counter}'
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:product_detail', kwargs={'slug': self.slug})

    @property
    def sizes_list(self):
        return [s.strip() for s in self.available_sizes.split(',') if s.strip()]

    @property
    def colors(self):
        """Colours this product comes in, from its variants, in COLORS order."""
        have = {v.color for v in self.variants.all() if v.color}
        return [c for c in COLORS if c in have]

    @property
    def is_on_sale(self):
        return bool(self.compare_at_price and self.compare_at_price > self.price)

    @property
    def discount_percent(self):
        if self.is_on_sale:
            return round((self.compare_at_price - self.price) / self.compare_at_price * 100)
        return 0

    @property
    def total_stock(self):
        return sum(v.stock_quantity for v in self.variants.all())

    @property
    def in_stock(self):
        return self.total_stock > 0

    @property
    def average_rating(self):
        agg = self.reviews.filter(is_approved=True).aggregate(models.Avg('rating'))
        return round(agg['rating__avg'] or 0, 1)

    @property
    def review_count(self):
        return self.reviews.filter(is_approved=True).count()

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        return img or self.images.first()


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=30, blank=True, choices=COLOR_CHOICES, help_text='Blank = shown for every colour.')

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return f'{self.product.name} image'


class ProductVariant(models.Model):
    """Colour + size combination: the unit that is stocked, carted and ordered."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField('variant ID', max_length=80, unique=True, blank=True)
    color = models.CharField(max_length=30, blank=True, choices=COLOR_CHOICES)
    size = models.CharField(max_length=10, choices=SIZE_CHOICES)
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=3)

    class Meta:
        unique_together = ('product', 'color', 'size')

    def __str__(self):
        return f'{self.product.name} - {self.color} {self.size} ({self.stock_quantity})'

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = make_variant_sku(self.product.sku, self.color, self.size)
        super().save(*args, **kwargs)

    @property
    def is_low_stock(self):
        return 0 < self.stock_quantity <= self.low_stock_threshold


def make_variant_sku(product_sku, color, size):
    """e.g. FX-OS-01 + Navy Blue + M -> FX-OS-01-NAVYBLUE-M"""
    return '-'.join(p for p in [product_sku, color.replace(' ', '').upper(), size] if p)


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(default=5)
    title = models.CharField(max_length=150, blank=True)
    comment = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')

    def __str__(self):
        return f'{self.user} - {self.product} ({self.rating}\u2605)'


class RecentlyViewed(models.Model):
    """Session-based recently-viewed tracking (local, no external service)."""
    session_key = models.CharField(max_length=64)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session_key', 'product')
        ordering = ['-viewed_at']
