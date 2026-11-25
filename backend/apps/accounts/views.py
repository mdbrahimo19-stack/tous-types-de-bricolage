from django.conf import settings
from django.shortcuts import render
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .otp import issue_otp, verify_otp
from .sms import SMSError
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

        try:
            _, code = issue_otp(phone, purpose)
        except SMSError:
            return Response(
                {"detail": "Envoi du SMS impossible pour le moment. Réessayez dans quelques minutes."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
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

        # loi 18-07 : pas d'inscription sans consentement explicite (vérifié AVANT de consommer le code)
        if purpose == "registration" and not data.get("accept_privacy"):
            return Response(
                {"detail": "Vous devez accepter la politique de confidentialité pour créer un compte.",
                 "code": "privacy_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
            if data.get("as_provider") and not user.is_provider:
                # client existant qui se connecte dans l'app BRICOOL Pro : il devient
                # aussi prestataire (profil « en attente », validé par l'équipe)
                user, _ = get_or_create_user_after_otp(phone, as_provider=True)
        else:  # registration (reset géré plus tard)
            user, created = get_or_create_user_after_otp(
                phone,
                full_name=data.get("full_name", ""),
                as_provider=data.get("as_provider", False),
                language=data.get("language", "fr"),
            )

        if not user.is_active:
            return Response({"detail": "Compte suspendu."}, status=status.HTTP_403_FORBIDDEN)

        if data.get("accept_privacy"):
            user.accept_privacy(settings.PRIVACY_POLICY_VERSION)

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


class MePrivacyView(APIView):
    """POST /api/auth/me/privacy/ : l'utilisateur accepte la version actuelle de la politique de confidentialité."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.accept_privacy(settings.PRIVACY_POLICY_VERSION)
        return Response(UserSerializer(request.user, context={"request": request}).data)


def privacy_policy(request):
    """Page publique « Politique de confidentialité » (français + arabe), liée depuis les deux apps."""
    ai_abroad = bool(getattr(settings, "AI_ENABLED", False))
    if ai_abroad:
        transfer = (
            "L'assistant intelligent (aide à décrire une demande, estimation de prix, aide) transmet les textes "
            "que vous lui écrivez à un prestataire d'intelligence artificielle situé hors d'Algérie. Ce transfert "
            "n'est effectué qu'avec l'autorisation préalable de l'ANPDP. N'écrivez pas d'informations sensibles "
            "à l'assistant. Toutes les autres données restent traitées en Algérie."
        )
        transfer_ar = (
            "يرسل المساعد الذكي النصوص التي تكتبها له إلى مزوّد ذكاء اصطناعي خارج الجزائر، ولا يتم ذلك إلا بترخيص "
            "مسبق من السلطة الوطنية. لا تكتب معلومات حساسة للمساعد. تبقى بقية المعطيات معالجة في الجزائر."
        )
    else:
        transfer = "Aucune donnée personnelle n'est transférée hors d'Algérie."
        transfer_ar = "لا يتم نقل أي معطيات شخصية إلى خارج الجزائر."
    context = {
        "version": settings.PRIVACY_POLICY_VERSION,
        "legal_name": settings.LEGAL_NAME,
        "legal_address": settings.LEGAL_ADDRESS,
        "contact_email": settings.PRIVACY_CONTACT_EMAIL,
        "dpo": settings.PRIVACY_DPO,
        "anpdp_ref": settings.ANPDP_DECLARATION_REF,
        "retention_years": settings.PRIVACY_RETENTION_YEARS,
        "transfer_text": transfer,
        "transfer_text_ar": transfer_ar,
    }
    return render(request, "legal/confidentialite.html", context)


MAX_PHOTO_BYTES = 5 * 1024 * 1024


class PhotoInSerializer(serializers.Serializer):
    photo = serializers.ImageField()

    def validate_photo(self, f):
        if f.size > MAX_PHOTO_BYTES:
            raise serializers.ValidationError("Photo trop lourde (5 Mo maximum).")
        return f


class MePhotoView(APIView):
    """Photo de profil : POST (multipart, champ « photo ») pour la changer, DELETE pour la retirer.

    Pour un artisan, c'est la photo que les clients voient sur ses devis."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = PhotoInSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = request.user
        if user.photo:
            user.photo.delete(save=False)  # pas de vieux fichiers orphelins
        user.photo = s.validated_data["photo"]
        user.save(update_fields=["photo"])
        return Response(UserSerializer(user, context={"request": request}).data)

    def delete(self, request):
        user = request.user
        if user.photo:
            user.photo.delete(save=False)
            user.photo = None
            user.save(update_fields=["photo"])
        return Response(UserSerializer(user, context={"request": request}).data)
