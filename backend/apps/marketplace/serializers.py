from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import ProviderProfile
from apps.catalog.models import Category, ProviderCategory
from apps.catalog.serializers import CategoryBriefSerializer
from apps.locations.geo import haversine_km
from apps.locations.models import Commune, Wilaya

from .models import (
    Conversation,
    Message,
    Mission,
    MissionPhoto,
    Notification,
    Quote,
    RequestPhoto,
    Review,
    ServiceRequest,
)


class RequestPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestPhoto
        fields = ("id", "image", "order", "created_at")
        read_only_fields = ("id", "created_at")


class ServiceRequestSerializer(serializers.ModelSerializer):
    category_detail = CategoryBriefSerializer(source="category", read_only=True)
    photos = RequestPhotoSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source="client.full_name", read_only=True)
    quotes_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "client_name", "category", "category_detail", "title", "description",
            "address", "wilaya", "commune", "latitude", "longitude",
            "urgency", "budget_min", "budget_max",
            "status", "published_at", "expires_at", "created_at", "updated_at",
            "photos", "quotes_count",
        )
        read_only_fields = (
            "status", "published_at", "expires_at", "created_at", "updated_at",
            "wilaya", "commune", "latitude", "longitude",
        )

    def validate_address(self, address):
        if address is not None and address.user_id != self.context["request"].user.id:
            raise serializers.ValidationError("Adresse inconnue.")
        return address

    def validate(self, attrs):
        address = attrs.get("address") or getattr(self.instance, "address", None)
        init = self.initial_data

        if address is not None:
            attrs["_loc"] = {
                "wilaya": address.wilaya, "commune": address.commune,
                "latitude": address.latitude, "longitude": address.longitude,
            }
        elif not self.instance:
            wilaya = _get_or_400(Wilaya, init.get("wilaya"))
            commune = _get_or_400(Commune, init.get("commune"))
            if wilaya is None or commune is None:
                raise serializers.ValidationError("Fournir `address`, ou `wilaya` + `commune`.")
            if commune.wilaya_id != wilaya.id:
                raise serializers.ValidationError({"commune": "Commune hors de la wilaya."})
            attrs["_loc"] = {
                "wilaya": wilaya, "commune": commune,
                "latitude": init.get("latitude") or None,
                "longitude": init.get("longitude") or None,
            }

        bmin, bmax = attrs.get("budget_min"), attrs.get("budget_max")
        if bmin is not None and bmax is not None and bmin > bmax:
            raise serializers.ValidationError({"budget_max": "Le budget max doit être ≥ au budget min."})
        return attrs

    def create(self, validated_data):
        loc = validated_data.pop("_loc", {})
        validated_data["client"] = self.context["request"].user
        validated_data.update(loc)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        loc = validated_data.pop("_loc", {})
        for field, value in loc.items():
            setattr(instance, field, value)
        return super().update(instance, validated_data)


def _get_or_400(model, pk):
    if not pk:
        return None
    try:
        return model.objects.get(pk=pk)
    except (model.DoesNotExist, TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
#  Prestataire : profil + catégories
# --------------------------------------------------------------------------
class ProviderCategorySerializer(serializers.ModelSerializer):
    category_detail = CategoryBriefSerializer(source="category", read_only=True)

    class Meta:
        model = ProviderCategory
        fields = (
            "id", "category", "category_detail",
            "years_experience", "hourly_rate", "flat_rate", "callout_fee",
        )

    def validate_category(self, category):
        if not category.is_active:
            raise serializers.ValidationError("Catégorie inactive.")
        return category


class ProviderSelfSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderProfile
        fields = (
            "business_name", "legal_status", "rc_number", "nif", "bio", "years_experience",
            "base_wilaya", "service_communes", "radius_km", "latitude", "longitude", "is_available",
            "verification_status", "rating_avg", "reviews_count", "missions_count",
        )
        read_only_fields = ("verification_status", "rating_avg", "reviews_count", "missions_count")


class ProviderPublicSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = ProviderProfile
        fields = (
            "id", "full_name", "business_name", "legal_status",
            "years_experience", "rating_avg", "reviews_count", "missions_count", "verification_status",
        )


# --------------------------------------------------------------------------
#  Fil des demandes (vue prestataire, coordonnées masquées — RG-04)
# --------------------------------------------------------------------------
class RequestFeedSerializer(serializers.ModelSerializer):
    category_detail = CategoryBriefSerializer(source="category", read_only=True)
    commune_name = serializers.CharField(source="commune.name_fr", read_only=True)
    wilaya_name = serializers.CharField(source="wilaya.name_fr", read_only=True)
    photos = RequestPhotoSerializer(many=True, read_only=True)
    distance_km = serializers.SerializerMethodField()
    already_quoted = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "category", "category_detail", "title", "description",
            "wilaya_name", "commune_name", "urgency", "budget_min", "budget_max",
            "status", "published_at", "photos", "distance_km", "already_quoted",
        )

    def get_distance_km(self, obj):
        prov = self.context.get("provider")
        if not prov:
            return None
        return haversine_km(obj.latitude, obj.longitude, prov.latitude, prov.longitude)

    def get_already_quoted(self, obj):
        return obj.id in self.context.get("quoted_ids", set())


# --------------------------------------------------------------------------
#  Devis
# --------------------------------------------------------------------------
class QuoteSerializer(serializers.ModelSerializer):
    provider_detail = serializers.SerializerMethodField()
    request_title = serializers.CharField(source="request.title", read_only=True)

    class Meta:
        model = Quote
        fields = (
            "id", "request", "request_title", "provider", "provider_detail", "amount", "lead_time_days",
            "estimated_duration", "message", "status", "valid_until", "created_at",
        )
        read_only_fields = fields

    def get_provider_detail(self, obj):
        profile = getattr(obj.provider, "provider_profile", None)
        return ProviderPublicSerializer(profile).data if profile else {"full_name": obj.provider.full_name}


class QuoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = ("amount", "lead_time_days", "estimated_duration", "message")

    def validate_amount(self, v):
        if v <= 0:
            raise serializers.ValidationError("Montant invalide.")
        return v


# --------------------------------------------------------------------------
#  Mission (coordonnées révélées après acceptation)
# --------------------------------------------------------------------------
class MissionSerializer(serializers.ModelSerializer):
    request_detail = serializers.SerializerMethodField()
    client_contact = serializers.SerializerMethodField()
    provider_contact = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = (
            "id", "request", "request_detail", "quote", "status", "scheduled_at",
            "confirmed_by_client", "confirmed_by_provider", "started_at", "ended_at",
            "amount_due", "payment_method", "paid_at", "payment_confirmed_by_provider",
            "client_contact", "provider_contact", "created_at",
        )
        read_only_fields = fields

    def get_request_detail(self, obj):
        r = obj.request
        addr = r.address
        return {
            "title": r.title,
            "description": r.description,
            "category": r.category.name_fr,
            "urgency": r.urgency,
            "wilaya": r.wilaya.name_fr,
            "commune": r.commune.name_fr,
            "street": addr.street if addr else "",
            "quartier": addr.quartier if addr else "",
            "notes": addr.notes if addr else "",
            "latitude": r.latitude,
            "longitude": r.longitude,
            "photos": RequestPhotoSerializer(r.photos.all(), many=True).data,
        }

    def get_client_contact(self, obj):
        u = obj.request.client
        return {"full_name": u.full_name, "phone": str(u.phone)}

    def get_provider_contact(self, obj):
        u = obj.provider
        profile = getattr(u, "provider_profile", None)
        return {
            "full_name": u.full_name,
            "phone": str(u.phone),
            "business_name": profile.business_name if profile else "",
        }


# --------------------------------------------------------------------------
#  Messagerie
# --------------------------------------------------------------------------
class MessageSerializer(serializers.ModelSerializer):
    sender_role = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id", "sender", "sender_role", "type", "body", "attachment",
            "was_filtered", "read_at", "flagged", "created_at",
        )
        read_only_fields = fields

    def get_sender_role(self, obj):
        if obj.type == Message.Type.SYSTEM:
            return "system"
        return "client" if obj.sender_id == obj.conversation.client_id else "provider"


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("type", "body", "attachment")

    def validate(self, attrs):
        mtype = attrs.get("type", Message.Type.TEXT)
        if mtype == Message.Type.TEXT and not attrs.get("body", "").strip():
            raise serializers.ValidationError({"body": "Message vide."})
        if mtype == Message.Type.PHOTO and not attrs.get("attachment"):
            raise serializers.ValidationError({"attachment": "Photo manquante."})
        return attrs


class ConversationSerializer(serializers.ModelSerializer):
    request_title = serializers.CharField(source="request.title", read_only=True)
    request_status = serializers.CharField(source="request.status", read_only=True)
    other_party = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    contacts_unlocked = serializers.BooleanField(read_only=True)

    class Meta:
        model = Conversation
        fields = (
            "id", "request", "request_title", "request_status", "other_party",
            "is_locked", "contacts_unlocked", "last_message", "last_message_at",
            "unread_count", "created_at",
        )

    def _me(self):
        return self.context["request"].user

    def get_other_party(self, obj):
        me = self._me()
        other = obj.provider if obj.client_id == me.id else obj.client
        profile = getattr(other, "provider_profile", None)
        return {
            "id": other.id,
            "full_name": other.full_name,
            "business_name": profile.business_name if (profile and obj.provider_id == other.id) else "",
        }

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        if not msg:
            return None
        return {"type": msg.type, "body": msg.body[:120], "created_at": msg.created_at}

    def get_unread_count(self, obj):
        me = self._me()
        return obj.messages.filter(read_at__isnull=True).exclude(sender=me).count()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "type", "title", "body", "data", "is_read", "created_at")
        read_only_fields = fields


# --------------------------------------------------------------------------
#  Suivi de mission
# --------------------------------------------------------------------------
class MissionPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissionPhoto
        fields = ("id", "kind", "image", "created_at")
        read_only_fields = ("id", "created_at")


class MissionScheduleSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()


# --------------------------------------------------------------------------
#  Évaluations
# --------------------------------------------------------------------------
class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model = Review
        fields = (
            "id", "mission", "author_name", "rating", "comment",
            "reply", "moderation_status", "created_at",
        )
        read_only_fields = fields


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ("rating", "comment")


class ProviderPublicProfileSerializer(serializers.ModelSerializer):
    """Fiche publique d'un prestataire (annuaire + détail). Pas de téléphone : le contact
    passe par une demande de devis et la messagerie de l'app."""

    full_name = serializers.CharField(source="user.full_name", read_only=True)
    photo = serializers.ImageField(source="user.photo", read_only=True)
    base_wilaya = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()

    class Meta:
        model = ProviderProfile
        fields = (
            "id", "full_name", "photo", "business_name", "legal_status", "bio", "years_experience",
            "base_wilaya", "rating_avg", "reviews_count", "missions_count", "is_available",
            "verification_status", "categories", "badges",
        )

    def get_base_wilaya(self, obj):
        w = obj.base_wilaya
        return {"id": w.id, "code": w.code, "name_fr": w.name_fr, "name_ar": w.name_ar} if w else None

    def get_categories(self, obj):
        # .all() profite du prefetch_related("categories__category") de la vue
        return [
            {
                "id": pc.category_id,
                "name_fr": pc.category.name_fr,
                "name_ar": pc.category.name_ar,
                "unit": pc.category.unit,
                "years_experience": pc.years_experience,
                "hourly_rate": pc.hourly_rate,
                "flat_rate": pc.flat_rate,
                "callout_fee": pc.callout_fee,
            }
            for pc in obj.categories.all()
        ]

    def get_badges(self, obj):
        badges = []
        if obj.verification_status == ProviderProfile.Verification.APPROVED:
            badges.append("identite_verifiee")
        if obj.legal_status != ProviderProfile.LegalStatus.UNDECLARED:
            badges.append("professionnel_declare")
        if obj.missions_count >= 20 and obj.rating_avg >= 4.5:
            badges.append("top_prestataire")
        return badges
