from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Address, Profile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone']

    def get_phone(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.phone if profile else ''


class MeUpdateSerializer(serializers.Serializer):
    """Backs GET/PATCH /api/accounts/me/ — updates span both the User
    model and its Profile, same fields templates/accounts/profile.html's
    ProfileForm exposed."""

    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def update(self, instance, validated_data):
        for field in ('first_name', 'last_name', 'email'):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        if 'phone' in validated_data:
            profile, _ = Profile.objects.get_or_create(user=instance)
            profile.phone = validated_data['phone']
            profile.save()
        return instance


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('A user with that username already exists.')
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
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password1'],
        )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'address_type', 'full_name', 'phone', 'line1', 'line2',
            'city', 'state', 'postal_code', 'country', 'is_default',
        ]
        read_only_fields = ['id']
