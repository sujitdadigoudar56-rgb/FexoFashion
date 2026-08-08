from .models import SiteSettings


def site_settings(request):
    """Expose the singleton SiteSettings row everywhere so admins can control
    site name, tagline, and contact info from /admin/ without touching code."""
    settings_obj = SiteSettings.objects.first()
    if settings_obj is None:
        settings_obj = SiteSettings(site_name='FEXO', tagline='Live in Fashion')
    return {'site_settings': settings_obj}
