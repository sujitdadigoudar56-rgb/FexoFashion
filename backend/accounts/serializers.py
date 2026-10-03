import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Address, Profile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()
    date_of_birth = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 'phone',
            'date_of_birth', 'avatar', 'date_joined',
        ]
        read_only_fields = ['date_joined']

    def _profile(self, obj):
        return Profile.objects.filter(user=obj).first()

    def get_phone(self, obj):
        profile = self._profile(obj)
        return profile.phone if profile else ''

    def get_date_of_birth(self, obj):
        profile = self._profile(obj)
        return profile.date_of_birth.isoformat() if profile and profile.date_of_birth else None

    def get_avatar(self, obj):
        profile = self._profile(obj)
        if not profile or not profile.avatar:
            return None
        url = profile.avatar.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request and url.startswith('/') else url


class MeUpdateSerializer(serializers.Serializer):
    """Backs GET/PATCH /api/accounts/me/ — updates span both the User
    model and its Profile, same fields templates/accounts/profile.html's
    ProfileForm exposed."""

    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def update(self, instance, validated_data):
        for field in ('first_name', 'last_name', 'email'):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        profile_fields = [f for f in ('phone', 'date_of_birth') if f in validated_data]
        if profile_fields:
            profile, _ = Profile.objects.get_or_create(user=instance)
            for field in profile_fields:
                setattr(profile, field, validated_data[field])
            profile.save()
        return instance


def _username_from_email(email):
    """Customers sign up with their email (the form has no username
    field), but Django's User still needs a unique username, so derive one
    from the email's local part."""
    base = re.sub(r'[^\w.@+-]', '', email.split('@')[0])[:140] or 'user'
    candidate, n = base, 1
    while User.objects.filter(username__iexact=candidate).exists():
        n += 1
        candidate = f'{base}{n}'
    return candidate


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    # Optional: generated from the email when omitted.
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    newsletter_opt_in = serializers.BooleanField(required=False, default=False)

    def validate_username(self, value):
        if value and User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with that username already exists.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate(self, attrs):
        if attrs['password1'] != attrs['password2']:
            raise serializers.ValidationError({'password2': ['Passwords do not match.']})
        try:
            validate_password(attrs['password1'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password1': list(exc.messages)})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data.get('username') or _username_from_email(validated_data['email']),
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password1'],
        )
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.phone = validated_data.get('phone', '')
        profile.newsletter_opt_in = validated_data.get('newsletter_opt_in', False)
        profile.save()
        return user


class LoginSerializer(serializers.Serializer):
    # Email, mobile number or username.
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': ['Your current password is incorrect.']})
        try:
            validate_password(attrs['new_password'], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'new_password': list(exc.messages)})
        return attrs


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'address_type', 'full_name', 'phone', 'line1', 'line2',
            'city', 'state', 'postal_code', 'country', 'is_default',
        ]
        read_only_fields = ['id']
