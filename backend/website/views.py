from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Banner, BlogPost, FAQ, InstagramPost, SiteSettings, Testimonial
from .serializers import (
    BannerSerializer,
    BlogPostSerializer,
    ContactMessageSerializer,
    FAQSerializer,
    InstagramPostSerializer,
    NewsletterSubscriberSerializer,
    SiteSettingsSerializer,
    TestimonialSerializer,
)

# about/privacy-policy/terms/shipping/returns had no model-backed content
# in the original app (plain `render(request, 'website/x.html')` with no
# context) — that prose now lives directly in the Next.js pages, so there's
# nothing to serve an API for.


class BannerListAPIView(generics.ListAPIView):
    queryset = Banner.objects.filter(is_active=True)
    serializer_class = BannerSerializer
    pagination_class = None


class TestimonialListAPIView(generics.ListAPIView):
    queryset = Testimonial.objects.filter(is_active=True)
    serializer_class = TestimonialSerializer
    pagination_class = None


class InstagramPostListAPIView(generics.ListAPIView):
    queryset = InstagramPost.objects.filter(is_active=True)
    serializer_class = InstagramPostSerializer
    pagination_class = None


class BlogPostListAPIView(generics.ListAPIView):
    queryset = BlogPost.objects.filter(is_published=True)
    serializer_class = BlogPostSerializer
    pagination_class = None


class BlogPostDetailAPIView(generics.RetrieveAPIView):
    queryset = BlogPost.objects.filter(is_published=True)
    serializer_class = BlogPostSerializer
    lookup_field = 'slug'


class FAQListAPIView(generics.ListAPIView):
    queryset = FAQ.objects.filter(is_active=True)
    serializer_class = FAQSerializer
    pagination_class = None


class SiteSettingsAPIView(APIView):
    """GET /api/site-settings/ — the one SiteSettings row (admin-editable
    singleton), same as the site_settings context processor exposed to
    every template before."""

    def get(self, request):
        settings_obj = SiteSettings.objects.first()
        if settings_obj is None:
            return Response({
                'site_name': 'FEXO', 'tagline': 'Live in Fashion',
                'contact_email': '', 'contact_phone': '',
                'address': '', 'instagram_url': '', 'facebook_url': '', 'twitter_url': '',
            })
        return Response(SiteSettingsSerializer(settings_obj).data)


class ContactCreateAPIView(generics.CreateAPIView):
    serializer_class = ContactMessageSerializer


class NewsletterCreateAPIView(APIView):
    def post(self, request):
        serializer = NewsletterSubscriberSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'detail': 'Subscribed! Welcome to the FEXO inner circle.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
