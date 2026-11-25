import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import chargily, services
from .models import Payment

logger = logging.getLogger("ttb.billing")

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
        fields = ("id", "method", "points", "amount_da", "reference", "status", "admin_note", "created_at",
                  "reviewed_at")


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


class CardPaymentView(APIView):
    """POST /api/provider/payments/card/ : page de paiement Chargily (Edahabia / CIB) pour les points dus."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = _profile(request.user)
        done = request.build_absolute_uri(reverse("billing:card-done"))
        webhook = ""
        if settings.PUBLIC_BASE_URL.startswith("https://"):
            webhook = settings.PUBLIC_BASE_URL + reverse("billing:chargily-webhook")
        payment, checkout_url = services.start_card_payment(
            profile,
            success_url=f"{done}?r=ok",
            failure_url=f"{done}?r=ko",
            webhook_url=webhook,
            locale=getattr(request.user, "language", "fr") or "fr",
        )
        return Response({"payment_id": payment.pk, "checkout_url": checkout_url}, status=status.HTTP_201_CREATED)


class CardPaymentSyncView(APIView):
    """POST /api/provider/payments/<id>/sync/ : au retour dans l'app, relit le statut chez Chargily."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        profile = _profile(request.user)
        payment = Payment.objects.filter(pk=pk, account__provider=profile, method=Payment.Method.CARD).first()
        if payment is None:
            raise NotFound("Paiement introuvable.")
        payment = services.sync_card_payment(payment)
        return Response(PaymentOutSerializer(payment).data)


@csrf_exempt
@require_POST
def chargily_webhook(request):
    """Confirmation envoyée par Chargily. Refusée si la signature ne correspond pas à notre clé."""
    raw = request.body
    if not chargily.valid_signature(raw, request.headers.get("signature")):
        logger.warning("Webhook Chargily refusé : signature invalide")
        return HttpResponse(status=403)
    try:
        event = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)
    services.handle_chargily_event(event)
    return HttpResponse("ok")


def card_done(request):
    """Page affichée après le paiement : on invite l'artisan à revenir dans BRICOOL Pro."""
    ok = request.GET.get("r") == "ok"
    title = "Paiement reçu ✔" if ok else "Paiement non abouti"
    text = (
        "Merci ! Revenez dans l'application BRICOOL Pro : votre compte se met à jour tout seul."
        if ok
        else "Le paiement n'a pas été effectué. Revenez dans BRICOOL Pro pour réessayer."
    )
    text_ar = (
        "شكراً! عد إلى تطبيق BRICOOL Pro: يتم تحديث حسابك تلقائياً."
        if ok
        else "لم تتم عملية الدفع. عد إلى BRICOOL Pro للمحاولة مجدداً."
    )
    color = "#0E7A55" if ok else "#9A2B12"
    html = (
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'><title>BRICOOL Pro</title></head>"
        "<body style='margin:0;font-family:system-ui,sans-serif;background:#F3F5F9;color:#141B26'>"
        "<div style='max-width:480px;margin:0 auto;padding:48px 20px;text-align:center'>"
        f"<h1 style='color:{color};font-size:24px'>{escape(title)}</h1>"
        f"<p style='font-size:16px;line-height:1.5'>{escape(text)}</p>"
        f"<p dir='rtl' style='font-size:16px;line-height:1.6'>{escape(text_ar)}</p>"
        "</div></body></html>"
    )
    return HttpResponse(html)
