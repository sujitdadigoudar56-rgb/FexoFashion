from django.db import migrations, models

COLOR_CHOICES = [(c, c) for c in [
    'Gray', 'Navy Blue', 'Black', 'Brown', 'Charcoal', 'White',
    'Beige', 'Maroon', 'Cement Gray', 'Cream', 'Olive Green',
]]


def move_colour_to_variants(apps, schema_editor):
    """Each product's single colour becomes the colour of its variants and images;
    every variant gets a variant ID (SKU-COLOUR-SIZE)."""
    Product = apps.get_model('products', 'Product')
    for product in Product.objects.all():
        product.images.update(color=product.color)
        for v in product.variants.all():
            v.color = product.color
            v.sku = '-'.join(p for p in [product.sku, product.color.replace(' ', '').upper(), v.size] if p)
            v.save(update_fields=['color', 'sku'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_color_choices_variant_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvariant',
            name='color',
            field=models.CharField(blank=True, choices=COLOR_CHOICES, max_length=30),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='sku',
            field=models.CharField(blank=True, max_length=80, verbose_name='variant ID'),
        ),
        migrations.AddField(
            model_name='productimage',
            name='color',
            field=models.CharField(blank=True, choices=COLOR_CHOICES, help_text='Blank = shown for every colour.', max_length=30),
        ),
        migrations.RunPython(move_colour_to_variants, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='productvariant',
            name='sku',
            field=models.CharField(blank=True, max_length=80, unique=True, verbose_name='variant ID'),
        ),
        migrations.AlterUniqueTogether(
            name='productvariant',
            unique_together={('product', 'color', 'size')},
        ),
        migrations.RemoveField(model_name='product', name='color'),
        migrations.RemoveField(model_name='product', name='variant_group'),
    ]
