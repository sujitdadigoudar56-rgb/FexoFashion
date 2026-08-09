import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = (
        'Creates (or resets the password of) the admin superuser from the '
        'DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD environment '
        'variables. Exists because the hosted deploy has no shell access to '
        'run `createsuperuser` interactively. Does nothing at all unless '
        'both username and password are set, and never fails the deploy.'
    )

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '').strip()
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()

        if not username or not password:
            self.stdout.write('No DJANGO_SUPERUSER_USERNAME/_PASSWORD set — skipping.')
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'is_staff': True, 'is_superuser': True},
        )

        # Re-applied on every boot so these env vars double as a password
        # reset: change the value in the host's dashboard, redeploy, done.
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        if email:
            user.email = email
        user.save()

        verb = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{verb} superuser "{username}".'))
