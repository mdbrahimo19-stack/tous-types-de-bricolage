from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Category
from apps.locations.models import Wilaya

from . import services
from .client import AIUnavailable

MAX_SUPPORT_TURNS = 20


class _AIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "ai"

    def handle_exception(self, exc):
        if isinstance(exc, AIUnavailable):
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return super().handle_exception(exc)


# --- Assistant de demande ------------------------------------------------
class DraftRequestInput(serializers.Serializer):
    text = serializers.CharField(min_length=5, max_length=2000)


class DraftRequestView(_AIView):
    """Texte libre (FR / AR / darija) -> brouillon pré-rempli pour POST /api/requests/."""

    def post(self, request):
        s = DraftRequestInput(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(services.draft_request(s.validated_data["text"]))


# --- Estimation de prix --------------------------------------------------
class PriceEstimateInput(serializers.Serializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.filter(is_active=True))
    description = serializers.CharField(min_length=5, max_length=2000)
    urgency = serializers.ChoiceField(choices=services.URGENCIES, default="this_week")
    wilaya = serializers.PrimaryKeyRelatedField(queryset=Wilaya.objects.all(), required=False, allow_null=True)
    language = serializers.ChoiceField(choices=["fr", "ar"], required=False)


class PriceEstimateView(_AIView):
    def post(self, request):
        s = PriceEstimateInput(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        return Response(services.estimate_price(
            d["category"], d["description"], d["urgency"], d.get("wilaya"),
            d.get("language") or request.user.language,
        ))


# --- Chatbot support -----------------------------------------------------
class SupportTurn(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(max_length=2000)


class SupportInput(serializers.Serializer):
    messages = SupportTurn(many=True, allow_empty=False)

    def validate_messages(self, turns):
        if turns[-1]["role"] != "user":
            raise serializers.ValidationError("Le dernier message doit venir de l'utilisateur.")
        turns = turns[-MAX_SUPPORT_TURNS:]
        while turns and turns[0]["role"] != "user":  # l'API exige de commencer par l'utilisateur
            turns = turns[1:]
        return turns


class SupportView(_AIView):
    """Sans état : l'app renvoie tout l'historique de la conversation à chaque tour."""

    def post(self, request):
        s = SupportInput(data=request.data)
        s.is_valid(raise_exception=True)
        history = [{"role": t["role"], "content": t["content"]} for t in s.validated_data["messages"]]
        return Response({"reply": services.support_reply(history)})
