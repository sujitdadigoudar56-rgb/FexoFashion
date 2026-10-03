import re

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Address, Profile
from .serializers import (
    AddressSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    MeUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterAPIView(APIView):
    """POST /api/accounts/register/ — creates the user and signs them in
    immediately (returns a token), same as register_view's login(request, user)."""

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {'token': token.key, 'user': UserSerializer(user, context={'request': request}).data},
            status=status.HTTP_201_CREATED,
        )


def _resolve_username(identifier):
    """Map the login identifier — email, mobile number or username — to
    the username Django's authenticate() expects."""
    identifier = identifier.strip()
    if '@' in identifier:
        user = User.objects.filter(email__iexact=identifier).order_by('pk').first()
        return user.get_username() if user else identifier
    digits = re.sub(r'\D', '', identifier)
    if len(digits) >= 10:
        # Match on the last 10 digits so "+91 98765 43210" == "9876543210".
        for profile in Profile.objects.select_related('user').exclude(phone=''):
            if re.sub(r'\D', '', profile.phone)[-10:] == digits[-10:]:
                return profile.user.get_username()
    return identifier


class LoginAPIView(APIView):
    """POST /api/accounts/login/ { username, password } — `username` may be
    an email address, mobile number or username."""

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=_resolve_username(serializer.validated_data['username']),
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response({'detail': 'Invalid email/mobile number or password.'}, status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': UserSerializer(user, context={'request': request}).data})


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeAPIView(APIView):
    """GET/PATCH /api/accounts/me/ — current user + profile, replaces
    dashboard_view/profile_view's combined user+Profile editing."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        serializer = MeUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user, context={'request': request}).data)


class AvatarUploadAPIView(APIView):
    """POST /api/accounts/me/avatar/ (multipart, field `avatar`)."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get('avatar')
        if not file:
            return Response({'avatar': ['Choose an image to upload.']}, status=status.HTTP_400_BAD_REQUEST)
        if file.size > 2 * 1024 * 1024:
            return Response({'avatar': ['Images must be 2 MB or smaller.']}, status=status.HTTP_400_BAD_REQUEST)
        if (file.content_type or '') not in ('image/jpeg', 'image/png', 'image/webp'):
            return Response({'avatar': ['Upload a JPG, PNG or WebP image.']}, status=status.HTTP_400_BAD_REQUEST)
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.avatar = file
        profile.save()
        return Response(UserSerializer(request.user, context={'request': request}).data)


class ChangePasswordAPIView(APIView):
    """POST /api/accounts/password/change/ { current_password, new_password }.
    The DRF token stays valid, so the user remains signed in."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'detail': 'Password updated.'})


class AddressListCreateAPIView(generics.ListCreateAPIView):
    """GET/POST /api/accounts/addresses/"""

    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if serializer.validated_data.get('is_default'):
            Address.objects.filter(user=self.request.user).update(is_default=False)
        serializer.save(user=self.request.user)


class AddressDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/accounts/addresses/<pk>/"""

    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.validated_data.get('is_default'):
            Address.objects.filter(user=self.request.user).exclude(pk=serializer.instance.pk).update(is_default=False)
        serializer.save()


class PasswordResetRequestAPIView(APIView):
    """POST /api/accounts/password-reset/ { email } — mirrors Django's
    PasswordResetForm, but builds the link against FRONTEND_URL (the
    Next.js app's own confirm page) instead of a Django template/view."""

    def post(self, request):
        email = (request.data.get('email') or '').strip()
        if email:
            for user in User.objects.filter(email__iexact=email, is_active=True):
                if not user.has_usable_password():
                    continue
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = f'{settings.FRONTEND_URL}/accounts/password-reset/confirm/{uid}/{token}'
                send_mail(
                    subject='Reset your FEXO password',
                    message=(
                        f'Hello {user.get_username()},\n\n'
                        'You requested a password reset for your FEXO account. '
                        f'Visit the link below to set a new password:\n\n{reset_url}\n\n'
                        "If you didn't request this, you can safely ignore this email.\n\n— FEXO"
                    ),
                    from_email=None,
                    recipient_list=[user.email],
                )
        # Always report success — don't leak whether the email is registered.
        return Response({'detail': 'If an account exists with that email, reset instructions are on the way.'})


class PasswordResetConfirmAPIView(APIView):
    """POST /api/accounts/password-reset/confirm/ { uid, token, new_password1, new_password2 }"""

    def post(self, request):
        uidb64 = request.data.get('uid', '')
        token = request.data.get('token', '')
        password1 = request.data.get('new_password1', '')
        password2 = request.data.get('new_password2', '')

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is None or not default_token_generator.check_token(user, token):
            return Response({'detail': 'This reset link is invalid or has expired.'}, status=status.HTTP_400_BAD_REQUEST)

        if not password1 or password1 != password2:
            return Response({'detail': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(password1, user=user)
        except DjangoValidationError as exc:
            return Response({'detail': list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password1)
        user.save()
        return Response({'detail': 'Password updated.'})
