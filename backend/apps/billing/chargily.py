"""Client minimal de Chargily Pay V2 (cartes Edahabia et CIB).

Documentation : https://dev.chargily.com/pay-v2/
- POST {api}/checkouts       crée une page de paiement (renvoie id + checkout_url)
- GET  {api}/checkouts/{id}  relit son statut (pending, paid, failed, canceled, expired)
- Webhook : en-tête « signature » = HMAC-SHA256 (hex) du corps brut, avec la clé secrète.

La clé secrète (CHARGILY_SECRET_KEY) reste dans le fichier .env du serveur : jamais dans
le code, jamais dans l'application mobile.
"""
import hashlib
import hmac
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger("ttb.billing")

TIMEOUT_SECONDS = 15


class ChargilyError(Exception):
    """Chargily injoignable ou requête refusée (message lisible par le bricoleur)."""


def enabled() -> bool:
    return bool(settings.CHARGILY_SECRET_KEY)


def _api_url() -> str:
    live = settings.CHARGILY_MODE == "live"
    return "https://pay.chargily.net/api/v2" if live else "https://pay.chargily.net/test/api/v2"


def _call(method: str, path: str, body: dict | None = None) -> dict:
    if not enabled():
        raise ChargilyError("Le paiement par carte n'est pas encore activé.")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = Request(
        f"{_api_url()}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {settings.CHARGILY_SECRET_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        logger.warning("Chargily %s %s -> HTTP %s %s", method, path, exc.code, detail)
        raise ChargilyError("Le service de paiement a refusé la demande. Réessayez plus tard.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        logger.warning("Chargily injoignable (%s %s) : %s", method, path, exc)
        raise ChargilyError("Service de paiement injoignable. Vérifiez votre connexion et réessayez.") from exc


def create_checkout(*, amount_da: int, success_url: str, failure_url: str, webhook_url: str = "",
                    metadata: dict | None = None, locale: str = "fr", description: str = "",
                    payer: dict | None = None) -> dict:  # payer : inutile chez Chargily
    body = {
        "amount": int(amount_da),
        "currency": "dzd",
        "success_url": success_url,
        "failure_url": failure_url,
        "locale": locale if locale in ("ar", "fr", "en") else "fr",
        "description": description[:255],
        "metadata": metadata or {},
    }
    if webhook_url:
        body["webhook_endpoint"] = webhook_url
    checkout = _call("POST", "/checkouts", body)
    if not checkout.get("id") or not checkout.get("checkout_url"):
        raise ChargilyError("Réponse inattendue du service de paiement.")
    return checkout


def retrieve_checkout(checkout_id: str) -> dict:
    return _call("GET", f"/checkouts/{checkout_id}")


def cancel_checkout(checkout_id: str) -> None:
    """Chargily n'a pas de suppression : une page non payée expire d'elle-même."""


def valid_signature(raw_body: bytes, signature: str | None) -> bool:
    """Vrai si le webhook vient bien de Chargily (signé avec notre clé secrète)."""
    if not signature or not enabled():
        return False
    expected = hmac.new(settings.CHARGILY_SECRET_KEY.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())
