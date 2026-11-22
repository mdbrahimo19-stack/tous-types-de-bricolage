from django.urls import reverse
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Payment

MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024


def _profile(user):
    profile = getattr(user, "provider_profile", None)
    if profile is None:
        raise PermissionDenied("Réservé aux bricoleurs.")
    return profile


class PointsView(APIView):
    """GET /api/provider/points/ : solde, blocage, coordonnées BaridiMob, historique."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.summary(_profile(request.user)))


class PaymentInSerializer(serializers.Serializer):
    screenshot = serializers.ImageField()
    reference = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")

    def validate_screenshot(self, f):
        if f.size > MAX_SCREENSHOT_BYTES:
            raise serializers.ValidationError("Image trop lourde (8 Mo maximum).")
        return f


class PaymentOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "points", "amount_da", "reference", "status", "admin_note", "created_at", "reviewed_at")


class PaymentsView(APIView):
    """GET : mes paiements. POST (multipart) : capture BaridiMob + référence."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        account = services.account_for(_profile(request.user))
        return Response(PaymentOutSerializer(account.payments.all()[:20], many=True).data)

    def post(self, request):
        profile = _profile(request.user)
        s = PaymentInSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        to_check = reverse("admin:billing_payment_changelist") + "?status__exact=pending"
        payment = services.submit_payment(
            profile,
            screenshot=s.validated_data["screenshot"],
            reference=s.validated_data["reference"],
            admin_url=request.build_absolute_uri(to_check),
        )
        return Response(PaymentOutSerializer(payment).data, status=status.HTTP_201_CREATED)
