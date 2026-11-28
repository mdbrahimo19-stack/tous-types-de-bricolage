from django.db import transaction
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from .models import ClientProfile, ProviderProfile, User

PURPOSES = ["registration", "login", "password_reset"]


class OTPRequestSerializer(serializers.Serializer):
    phone = PhoneNumberField(region="DZ")
    purpose = serializers.ChoiceField(choices=PURPOSES, default="registration")


class OTPVerifySerializer(serializers.Serializer):
    phone = PhoneNumberField(region="DZ")
    code = serializers.CharField(min_length=4, max_length=8, trim_whitespace=True)
    purpose = serializers.ChoiceField(choices=PURPOSES, default="registration")
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    as_provider = serializers.BooleanField(required=False, default=False)
    language = serializers.ChoiceField(choices=["fr", "ar", "en"], required=False, default="fr")
    # consentement explicite à la politique de confidentialité (obligatoire à l'inscription)
    accept_privacy = serializers.BooleanField(required=False, default=False)


class ProviderProfileSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProviderProfile
        fields = (
            "business_name", "legal_status", "rc_number", "nif", "bio", "years_experience",
            "base_wilaya", "service_communes", "radius_km", "verification_status", "is_verified",
            "rating_avg", "reviews_count", "missions_count", "is_available",
        )
        read_only_fields = ("verification_status", "is_verified", "rating_avg", "reviews_count", "missions_count")


class ClientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientProfile
        fields = ("reliability_score",)
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    client_profile = ClientProfileSerializer(read_only=True)
    provider_profile = ProviderProfileSerializer(read_only=True)
    # vrai tant que l'utilisateur n'a pas accepté la version actuelle de la politique
    privacy_required = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "phone", "email", "full_name", "photo", "is_client", "is_provider",
            "phone_verified", "language", "date_joined", "client_profile", "provider_profile",
            "privacy_version", "privacy_accepted_at", "privacy_required",
        )
        read_only_fields = ("id", "phone", "is_client", "is_provider", "phone_verified", "date_joined",
                            "privacy_version", "privacy_accepted_at")

    def get_privacy_required(self, obj):
        from django.conf import settings

        return obj.privacy_version != settings.PRIVACY_POLICY_VERSION


@transaction.atomic
def get_or_create_user_after_otp(phone, *, full_name="", as_provider=False, language="fr") -> tuple[User, bool]:
    user, created = User.objects.get_or_create(
        phone=phone,
        defaults={"full_name": full_name, "language": language, "phone_verified": True},
    )
    changed = []
    if not user.phone_verified:
        user.phone_verified = True
        changed.append("phone_verified")
    if full_name and not user.full_name:
        user.full_name = full_name
        changed.append("full_name")
    if as_provider and not user.is_provider:
        user.is_provider = True
        changed.append("is_provider")
    if changed:
        user.save(update_fields=changed)

    ClientProfile.objects.get_or_create(user=user)
    if user.is_provider:
        ProviderProfile.objects.get_or_create(user=user)
    return user, created
