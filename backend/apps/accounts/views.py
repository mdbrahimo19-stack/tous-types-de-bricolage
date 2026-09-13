from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .otp import issue_otp, verify_otp
from .serializers import (
    OTPRequestSerializer,
    OTPVerifySerializer,
    UserSerializer,
    get_or_create_user_after_otp,
)


def _tokens_for(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class OTPRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def post(self, request):
        s = OTPRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        phone = s.validated_data["phone"]
        purpose = s.validated_data["purpose"]

        if purpose == "login" and not User.objects.filter(phone=phone).exists():
            return Response(
                {"detail": "Aucun compte associé à ce numéro."}, status=status.HTTP_404_NOT_FOUND
            )

        _, code = issue_otp(phone, purpose)
        payload = {"detail": "Code envoyé par SMS.", "expires_in": settings.OTP_TTL_SECONDS}
        if settings.OTP_EXPOSE_IN_RESPONSE:
            payload["debug_code"] = code  # uniquement en DEBUG
        return Response(payload, status=status.HTTP_200_OK)


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        s = OTPVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        phone, code, purpose = data["phone"], data["code"], data["purpose"]

        if not verify_otp(phone, code, purpose):
            return Response(
                {"detail": "Code invalide ou expiré."}, status=status.HTTP_400_BAD_REQUEST
            )

        if purpose == "login":
            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                return Response({"detail": "Compte introuvable."}, status=status.HTTP_404_NOT_FOUND)
            created = False
        else:  # registration (reset géré plus tard)
            user, created = get_or_create_user_after_otp(
                phone,
                full_name=data.get("full_name", ""),
                as_provider=data.get("as_provider", False),
                language=data.get("language", "fr"),
            )

        if not user.is_active:
            return Response({"detail": "Compte suspendu."}, status=status.HTTP_403_FORBIDDEN)

        return Response(
            {
                "created": created,
                "tokens": _tokens_for(user),
                "user": UserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            RefreshToken(request.data["refresh"]).blacklist()
        except Exception:
            return Response({"detail": "Jeton refresh manquant ou invalide."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
