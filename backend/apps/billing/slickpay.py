"""Client minimal de Slick-Pay (cartes CIB et Edahabia, page de paiement SATIM).

Constaté sur l'API réelle (v2) le 25/11/2026 :
- POST /users/invoices          -> {"success", "id", "url", "invoice": {...}} ; "url" = page de paiement SATIM
- GET  /users/invoices/{id}     -> {"completed": 0|1, "data": {"completed", "amount": "100.00", "status", ...}}
- DELETE /users/invoices/{id}   -> supprime une facture non payée
- GET  /users/accounts          -> comptes de versement (CCP / banque) ; "uuid" à donner dans "account"
- L'API refuse les clients HTTP qui ne se présentent pas : on envoie un User-Agent explicite.

Sécurité : les messages envoyés par Slick-Pay ne sont pas signés de façon fiable, donc BRICOOL ne
s'y fie jamais. Un paiement n'est validé qu'après avoir relu la facture chez Slick-Pay
(completed == 1 et montant suffisant). La clé reste dans le .env du serveur.
"""
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("ttb.billing")

TIMEOUT_SECONDS = 20
USER_AGENT = "BRICOOL-backend/1.0"
_ACCOUNT_CACHE_KEY = "slickpay:account_uuid"


class SlickPayError(Exception):
    """Slick-Pay injoignable ou requête refusée (message lisible par le bricoleur)."""


class _NotFound(SlickPayError):
    pass


def enabled() -> bool:
    return bool(settings.SLICKPAY_PUBLIC_KEY)


def _api_url() -> str:
    if settings.SLICKPAY_SANDBOX:
        return "https://devapi.slick-pay.com/api/v2"
    return "https://prodapi.slick-pay.com/api/v2"


def _call(method: str, path: str, body: dict | None = None) -> dict:
    if not enabled():
        raise SlickPayError("Le paiement par carte n'est pas encore activé.")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = Request(
        f"{_api_url()}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {settings.SLICKPAY_PUBLIC_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        logger.warning("Slick-Pay %s %s -> HTTP %s %s", method, path, exc.code, detail)
        if exc.code == 404:
            raise _NotFound("Facture introuvable.") from exc
        raise SlickPayError("Le service de paiement a refusé la demande. Réessayez plus tard.") from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        logger.warning("Slick-Pay injoignable (%s %s) : %s", method, path, exc)
        raise SlickPayError("Service de paiement injoignable. Vérifiez votre connexion et réessayez.") from exc


def _account_uuid() -> str:
    """Compte CCP / bancaire qui reçoit l'argent (celui « par défaut » dans Slick-Pay)."""
    cached = cache.get(_ACCOUNT_CACHE_KEY)
    if cached:
        return cached
    accounts = _call("GET", "/users/accounts").get("data") or []
    if not accounts:
        raise SlickPayError("Aucun compte de versement n'est configuré chez Slick-Pay.")
    chosen = next((a for a in accounts if str(a.get("default")) == "1"), accounts[0])
    uuid = str(chosen.get("uuid") or "")
    if not uuid:
        raise SlickPayError("Compte de versement Slick-Pay invalide.")
    cache.set(_ACCOUNT_CACHE_KEY, uuid, 3600)
    return uuid


def create_checkout(*, amount_da: int, success_url: str, failure_url: str = "", webhook_url: str = "",
                    metadata: dict | None = None, locale: str = "fr", description: str = "",
                    payer: dict | None = None) -> dict:
    """Crée une facture Slick-Pay. Renvoie {"id", "checkout_url"} comme le client Chargily."""
    payer = payer or {}
    body = {
        "amount": int(amount_da),
        "account": _account_uuid(),
        "firstname": (payer.get("firstname") or "Artisan")[:60],
        "lastname": (payer.get("lastname") or "BRICOOL")[:60],
        "phone": payer.get("phone") or "",
        "email": payer.get("email") or "",
        "address": payer.get("address") or "Algérie",
        "url": success_url,  # Slick-Pay n'a qu'une adresse de retour
        "items": [{"name": (description or "BRICOOL Pro")[:120], "price": int(amount_da), "quantity": 1}],
    }
    if webhook_url:
        body["webhook_url"] = webhook_url
        body["webhook_meta_data"] = metadata or {}
    resp = _call("POST", "/users/invoices", body)
    invoice = resp.get("invoice") if isinstance(resp.get("invoice"), dict) else {}
    invoice_id = resp.get("id") or invoice.get("id")
    url = resp.get("url") or invoice.get("url")
    if not invoice_id or not url:
        raise SlickPayError("Réponse inattendue du service de paiement.")
    return {"id": str(invoice_id), "checkout_url": url}


def retrieve_checkout(invoice_id: str) -> dict:
    """Statut normalisé : {"status": "paid" | "pending" | "failed", "amount": float}."""
    try:
        resp = _call("GET", f"/users/invoices/{invoice_id}")
    except _NotFound:
        return {"status": "failed", "amount": 0}  # facture supprimée chez Slick-Pay
    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    completed = data.get("completed", resp.get("completed"))
    try:
        amount = float(data.get("amount") or 0)
    except (TypeError, ValueError):
        amount = 0.0
    paid = str(completed) == "1"
    return {"status": "paid" if paid else "pending", "amount": amount}


def cancel_checkout(invoice_id: str) -> None:
    """Supprime une facture non payée (elle ne pourra plus être payée par erreur)."""
    try:
        _call("DELETE", f"/users/invoices/{invoice_id}")
    except SlickPayError:
        logger.info("Facture Slick-Pay %s non supprimée (déjà payée ou introuvable)", invoice_id)
