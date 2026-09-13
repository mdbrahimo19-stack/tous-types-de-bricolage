"""Génération et vérification des codes OTP (flow maison)."""
import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from .models import PhoneOTP
from .sms import send_sms


def _generate_code(length: int | None = None) -> str:
    length = length or settings.OTP_LENGTH
    return "".join(secrets.choice("0123456789") for _ in range(length))


def issue_otp(phone, purpose: str):
    """Crée un OTP, envoie le SMS, renvoie (otp, code_en_clair)."""
    code = _generate_code()
    otp = PhoneOTP.objects.create(
        phone=phone,
        code_hash=make_password(code),
        purpose=purpose,
        expires_at=PhoneOTP.default_expiry(),
    )
    send_sms(str(phone), f"Tous Types de Bricolages : votre code de vérification est {code}")
    return otp, code


def verify_otp(phone, code: str, purpose: str) -> bool:
    """Vérifie le dernier OTP non consommé pour (phone, purpose)."""
    otp = (
        PhoneOTP.objects
        .filter(phone=phone, purpose=purpose, consumed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if otp is None or not otp.is_valid:
        return False

    if check_password(code, otp.code_hash):
        otp.consumed_at = timezone.now()
        otp.save(update_fields=["consumed_at"])
        return True

    otp.attempts += 1
    otp.save(update_fields=["attempts"])
    return False
