"""Envoi de SMS - backend pluggable.

- `console` (dev) : écrit le message dans les logs / la console, rien n'est envoyé.
- `http` : POST JSON vers l'API d'un fournisseur SMS (agrégateur algérien, offre
  « SMS Pro » d'un opérateur, ou passerelle SMS installée sur un téléphone Android).
  Tout se règle dans le .env, sans toucher au code (voir docs/sms-aggregator-brief.md) :

    SMS_BACKEND=http
    SMS_API_URL=https://api.fournisseur.dz/v1/sms/send
    SMS_API_KEY=xxxxxxxx
    SMS_AUTH_HEADER=Authorization      # en-tête qui porte la clé
    SMS_AUTH_SCHEME=Bearer             # préfixe de la clé (vide = clé seule)
    SMS_SENDER_ID=TTB                  # expéditeur (vide = non envoyé)
    SMS_PHONE_FORMAT=e164              # e164 (+213…) | intl (213…) | local (0…)
    SMS_FIELD_TO=to                    # noms des champs JSON attendus par le fournisseur
    SMS_FIELD_TEXT=text
    SMS_FIELD_SENDER=sender
    SMS_EXTRA_JSON={}                  # champs fixes en plus, ex. {"type": "otp"}

Le reste du code ne dépend que de `send_sms`, qui lève `SMSError` si l'envoi échoue.
"""
import json
import logging
import time
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger("ttb.sms")

RETRIES = 1  # une nouvelle tentative en cas d'erreur réseau ou serveur (5xx)


class SMSError(Exception):
    """Le SMS n'a pas pu être envoyé (fournisseur injoignable, refus, mauvaise config)."""


def format_phone(phone: str, fmt: str) -> str:
    """+213555123456 -> e164 « +213555123456 », intl « 213555123456 », local « 0555123456 »."""
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0"):  # numéro local saisi tel quel
        digits = "213" + digits[1:]
    if fmt == "intl":
        return digits
    if fmt == "local":
        return "0" + digits[3:] if digits.startswith("213") else digits
    return "+" + digits


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

    if backend in ("http", "aggregator"):
        return _send_http(phone, message)

    if backend == "firebase":
        # Avec Firebase Phone Auth, l'envoi du SMS est fait par le SDK client.
        raise RuntimeError(
            "SMS_BACKEND=firebase : l'OTP est géré côté client par Firebase, "
            "n'appelle pas send_sms dans ce mode."
        )

    raise SMSError(f"SMS_BACKEND inconnu : {backend!r}")


def _send_http(phone: str, message: str) -> bool:
    url = settings.SMS_API_URL
    if not url:
        raise SMSError("SMS_BACKEND=http mais SMS_API_URL est vide.")

    body = dict(settings.SMS_EXTRA_JSON)
    body[settings.SMS_FIELD_TO] = format_phone(phone, settings.SMS_PHONE_FORMAT)
    body[settings.SMS_FIELD_TEXT] = message
    if settings.SMS_SENDER_ID:
        body[settings.SMS_FIELD_SENDER] = settings.SMS_SENDER_ID

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if settings.SMS_API_KEY:
        scheme = settings.SMS_AUTH_SCHEME.strip()
        headers[settings.SMS_AUTH_HEADER] = f"{scheme} {settings.SMS_API_KEY}" if scheme else settings.SMS_API_KEY

    data = json.dumps(body).encode("utf-8")
    masked = body[settings.SMS_FIELD_TO][:-4] + "****"  # jamais le numéro complet dans les logs

    for attempt in range(RETRIES + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=settings.SMS_TIMEOUT_SECONDS) as resp:
                logger.info("SMS envoyé à %s (HTTP %s)", masked, resp.status)
                return True
        except urllib.error.HTTPError as exc:
            # 4xx = refus définitif (clé, format, crédit épuisé) : inutile de réessayer
            detail = exc.read(300).decode("utf-8", "replace")
            logger.error("SMS refusé pour %s : HTTP %s %s", masked, exc.code, detail)
            if exc.code < 500 or attempt == RETRIES:
                raise SMSError(f"Fournisseur SMS : HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.error("Fournisseur SMS injoignable pour %s : %s", masked, exc)
            if attempt == RETRIES:
                raise SMSError("Fournisseur SMS injoignable") from exc
        time.sleep(1)
    return False  # pragma: no cover
