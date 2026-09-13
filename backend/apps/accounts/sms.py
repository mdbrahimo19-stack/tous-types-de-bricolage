"""Envoi de SMS - backend pluggable.

En dev : `console` écrit le message dans les logs / stdout.
Plus tard : ajouter un backend `firebase` (vérification d'ID token, pas d'envoi côté serveur)
ou un backend agrégateur local (envoi HTTP). Le reste du code ne dépend que de `send_sms`.
"""
import logging

from django.conf import settings

logger = logging.getLogger("ttb.sms")


def send_sms(phone: str, message: str) -> bool:
    backend = getattr(settings, "SMS_BACKEND", "console")

    if backend == "console":
        line = f"[SMS -> {phone}] {message}"
        logger.info(line)
        try:
            print(f"\n{line}\n", flush=True)
        except UnicodeEncodeError:  # console Windows en cp1252
            pass
        return True

    if backend == "firebase":
        # Avec Firebase Phone Auth, l'envoi du SMS est fait par le SDK client.
        # Le backend ne fait que vérifier l'ID token (voir otp.verify_firebase_token).
        raise RuntimeError(
            "SMS_BACKEND=firebase : l'OTP est géré côté client par Firebase, "
            "n'appelle pas send_sms dans ce mode."
        )

    raise NotImplementedError(f"SMS backend inconnu : {backend!r}")
