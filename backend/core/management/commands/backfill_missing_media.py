from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from categories.models import Category, Collection
from products.models import ProductImage
from website.models import Banner, BlogPost, InstagramPost


def _placeholder_image(text, size=(900, 1125), bg=(17, 17, 17)):
    import io

    from PIL import Image as PILImage
    from PIL import ImageDraw

    img = PILImage.new('RGB', size, color=bg)
    draw = ImageDraw.Draw(img)
    draw.text((size[0] / 2 - 40, size[1] / 2), text[:24], fill=(140, 140, 140))
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return ContentFile(buf.getvalue(), name=f'{slugify(text)[:40]}.jpg')


class Command(BaseCommand):
    help = (
        'Regenerates placeholder image files for any ImageField whose DB '
        'row references a filename that is missing from storage (e.g. '
        'after the DB was seeded on one machine/disk but the media files '
        'never made it to the disk actually serving requests).'
    )

    def handle(self, *args, **options):
        fixed = 0

        def backfill(obj, field_name, label, size=(900, 1125), bg=(17, 17, 17)):
            nonlocal fixed
            field = getattr(obj, field_name)
            if field and not default_storage.exists(field.name):
                field.save(field.name.split('/')[-1], _placeholder_image(label, size=size, bg=bg), save=True)
                fixed += 1
                self.stdout.write(f'  regenerated {field.name}')

        for c in Category.objects.all():
            backfill(c, 'image', c.name)
        for c in Collection.objects.all():
            backfill(c, 'banner_image', c.name, size=(1600, 600))
        for pi in ProductImage.objects.select_related('product').all():
            backfill(pi, 'image', pi.product.name)
        for b in Banner.objects.all():
            backfill(b, 'image', 'FEXO', size=(1600, 900), bg=(10, 10, 10))
        for ip in InstagramPost.objects.all():
            backfill(ip, 'image', 'fexo', size=(600, 600))
        for bp in BlogPost.objects.all():
            backfill(bp, 'cover_image', bp.title, size=(1200, 700))

        self.stdout.write(self.style.SUCCESS(f'Done. Regenerated {fixed} missing image file(s).'))
