"""Règles des points : débit à chaque contact, blocage, paiement (carte ou BaridiMob), déblocage."""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.marketplace.notifications import notify

from . import chargily
from .models import Payment, PointEntry, PointsAccount

logger = logging.getLogger("ttb.billing")


def account_for(profile):
    account, _ = PointsAccount.objects.get_or_create(provider=profile)
    return account


def is_blocked(profile):
    account = PointsAccount.objects.filter(provider=profile).first()
    return bool(account and account.blocked)


def _fmt_da(amount):
    return f"{amount:,} DA".replace(",", " ")


def blocked_message(account):
    return (
        f"Compte bloqué : réglez {_fmt_da(account.amount_due_da)} par carte Edahabia / CIB ou BaridiMob "
        "(onglet Profil → Mes points) pour recevoir de nouvelles demandes."
    )


def charge_contact(profile, mission):
    """Débite POINTS_PER_CONTACT points quand un client accepte le devis du bricoleur.

    Les points offerts partent en premier. Idempotent : une mission n'est débitée qu'une fois.
    """
    account_for(profile)
    cost = settings.POINTS_PER_CONTACT
    try:
        with transaction.atomic():
            account = PointsAccount.objects.select_for_update().get(provider=profile)
            if PointEntry.objects.filter(mission=mission, kind=PointEntry.Kind.CONTACT).exists():
                return account
            was_blocked = account.blocked
            free = min(account.free_points, cost)
            due = cost - free
            account.free_points -= free
            account.points_due += due
            account.save(update_fields=["free_points", "points_due", "updated_at"])
            PointEntry.objects.create(
                account=account, kind=PointEntry.Kind.CONTACT, free_used=free, due_delta=due,
                mission=mission, note=mission.request.title[:255],
            )
    except IntegrityError:  # débit déjà enregistré par une requête concurrente
        return PointsAccount.objects.get(provider=profile)

    if account.blocked and not was_blocked:
        notify(
            profile.user, "account_blocked", "Compte bloqué : paiement à faire",
            f"Vous avez atteint {account.points_due} points. "
            f"Réglez {_fmt_da(account.amount_due_da)} dans l'app (Mes points) : par carte, ou par BaridiMob.",
            data={"points_due": account.points_due},
        )
    return account


def submit_payment(profile, *, screenshot, reference="", admin_url=""):
    """Le bricoleur déclare avoir payé par BaridiMob et joint la capture."""
    account = account_for(profile)
    if account.points_due <= 0:
        raise ValidationError("Vous n'avez rien à payer pour l'instant.")
    pending = account.payments.filter(status=Payment.Status.PENDING)
    if pending.filter(method=Payment.Method.BARIDIMOB).exists():
        raise ValidationError("Un paiement est déjà en cours de vérification.")
    _close_card_pages(account, "Remplacé par un paiement BaridiMob.")
    account.refresh_from_db()
    if account.points_due <= 0:
        raise ValidationError("Votre paiement par carte vient d'être reçu : il n'y a plus rien à payer.")
    payment = Payment.objects.create(
        account=account,
        points=account.points_due,
        amount_da=account.amount_due_da,
        reference=reference.strip()[:80],
        screenshot=screenshot,
    )
    _email_admin(payment, admin_url)
    return payment


def _email_admin(payment, admin_url):
    to = settings.PAYMENTS_NOTIFY_EMAIL
    if not to:
        return
    provider = payment.account.provider
    lines = [
        "Nouveau paiement BaridiMob à vérifier.",
        "",
        f"Bricoleur : {provider} ({provider.user.phone})",
        f"Montant : {_fmt_da(payment.amount_da)} ({payment.points} points)",
        f"Référence : {payment.reference or '—'}",
        "",
        "Vérifiez la capture puis validez le paiement pour débloquer le compte :",
        admin_url or "/admin/billing/payment/",
    ]
    try:
        send_mail(
            f"Paiement BaridiMob à vérifier — {_fmt_da(payment.amount_da)}",
            "\n".join(lines), None, [to],
        )
    except Exception:  # l'email ne doit jamais bloquer l'envoi du paiement
        logger.exception("Email de paiement non envoyé (paiement %s)", payment.pk)


def approve_payment(payment, by=None):
    """L'administrateur a reçu l'argent : les points payés sont soldés, le compte est débloqué."""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status != Payment.Status.PENDING:
            return payment
        account = PointsAccount.objects.select_for_update().get(pk=payment.account_id)
        credited = min(payment.points, account.points_due)
        account.points_due -= credited
        account.save(update_fields=["points_due", "updated_at"])
        payment.status = Payment.Status.APPROVED
        payment.reviewed_at = timezone.now()
        payment.reviewed_by = by
        payment.save(update_fields=["status", "reviewed_at", "reviewed_by"])
        label = "par carte" if payment.method == Payment.Method.CARD else "BaridiMob"
        PointEntry.objects.create(
            account=account, kind=PointEntry.Kind.PAYMENT, due_delta=-credited, payment=payment,
            note=f"Paiement {label} {_fmt_da(payment.amount_da)}",
        )
    notify(
        account.provider.user, "payment_approved", "Paiement validé",
        f"Merci ! Votre paiement de {_fmt_da(payment.amount_da)} est validé"
        + (", votre compte est débloqué." if not account.blocked else "."),
        data={"payment_id": payment.id},
    )
    return payment


def reject_payment(payment, by=None, note=""):
    if payment.status != Payment.Status.PENDING:
        return payment
    payment.status = Payment.Status.REJECTED
    payment.reviewed_at = timezone.now()
    payment.reviewed_by = by
    if note:
        payment.admin_note = note[:255]
    payment.save(update_fields=["status", "reviewed_at", "reviewed_by", "admin_note"])
    notify(
        payment.account.provider.user, "payment_rejected", "Paiement non validé",
        payment.admin_note or "Le paiement n'a pas été retrouvé. Vérifiez la capture et renvoyez-la.",
        data={"payment_id": payment.id},
    )
    return payment


# ---------------------------------------------------------------------------
#  Paiement par carte Edahabia / CIB (Chargily Pay) : validé automatiquement
# ---------------------------------------------------------------------------
CARD_FAILED_STATUSES = {"failed", "canceled", "cancelled", "expired"}


def _cancel_card(payment, note):
    """Page de paiement par carte abandonnée / échouée / remplacée (sans notification)."""
    Payment.objects.filter(pk=payment.pk, status=Payment.Status.PENDING).update(
        status=Payment.Status.REJECTED, admin_note=note[:255], reviewed_at=timezone.now()
    )


def _close_card_pages(account, note):
    """Avant un nouveau paiement : une ancienne page par carte a peut-être été payée entre-temps."""
    for old in account.payments.filter(status=Payment.Status.PENDING, method=Payment.Method.CARD):
        sync_card_payment(old)
        old.refresh_from_db()
        if old.status == Payment.Status.PENDING:
            _cancel_card(old, note)


def start_card_payment(profile, *, success_url, failure_url, webhook_url="", locale="fr"):
    """Crée une page de paiement Chargily pour tous les points dus. Renvoie (paiement, adresse)."""
    if not chargily.enabled():
        raise ValidationError("Le paiement par carte n'est pas encore activé.")
    account = account_for(profile)
    if account.payments.filter(status=Payment.Status.PENDING, method=Payment.Method.BARIDIMOB).exists():
        raise ValidationError("Un paiement BaridiMob est déjà en cours de vérification.")
    _close_card_pages(account, "Remplacé par un nouveau paiement par carte.")
    account.refresh_from_db()
    if account.points_due <= 0:
        raise ValidationError("Vous n'avez rien à payer pour l'instant.")

    payment = Payment.objects.create(
        account=account, method=Payment.Method.CARD,
        points=account.points_due, amount_da=account.amount_due_da,
    )
    try:
        checkout = chargily.create_checkout(
            amount_da=payment.amount_da,
            success_url=success_url,
            failure_url=failure_url,
            webhook_url=webhook_url,
            metadata={"payment_id": str(payment.pk)},
            locale=locale,
            description=f"BRICOOL Pro : {payment.points} points",
        )
    except chargily.ChargilyError as exc:
        payment.delete()
        raise ValidationError(str(exc)) from exc
    payment.checkout_id = str(checkout["id"])
    payment.save(update_fields=["checkout_id"])
    return payment, checkout["checkout_url"]


def _apply_checkout(payment, checkout):
    """Applique le statut d'une page Chargily à notre paiement (payé -> points soldés)."""
    status = str(checkout.get("status") or "").lower()
    if status == "paid":
        try:
            paid_amount = int(float(checkout.get("amount") or 0))
        except (TypeError, ValueError):
            paid_amount = 0
        if paid_amount < payment.amount_da:
            logger.error("Paiement %s : montant Chargily %s < %s DA, non validé", payment.pk, paid_amount,
                         payment.amount_da)
            return payment
        return approve_payment(payment)
    if status in CARD_FAILED_STATUSES:
        _cancel_card(payment, "Paiement par carte non abouti.")
        payment.refresh_from_db()
    return payment


def sync_card_payment(payment):
    """Relit le statut chez Chargily (retour dans l'app, ou webhook impossible en local)."""
    if payment.method != Payment.Method.CARD or payment.status != Payment.Status.PENDING or not payment.checkout_id:
        return payment
    try:
        checkout = chargily.retrieve_checkout(payment.checkout_id)
    except chargily.ChargilyError:
        return payment  # on réessaiera plus tard
    return _apply_checkout(payment, checkout)


def handle_chargily_event(event):
    """Webhook Chargily (signature déjà vérifiée) : checkout.paid / checkout.failed / checkout.canceled."""
    data = event.get("data") or {}
    checkout_id = str(data.get("id") or "")
    if not checkout_id:
        return None
    payment = Payment.objects.filter(method=Payment.Method.CARD, checkout_id=checkout_id).first()
    if payment is None or payment.status != Payment.Status.PENDING:
        return payment
    kind = str(event.get("type") or "")
    if kind == "checkout.paid" and not data.get("status"):
        data = {**data, "status": "paid"}
    elif kind in ("checkout.failed", "checkout.canceled") and not data.get("status"):
        data = {**data, "status": "failed"}
    return _apply_checkout(payment, data)


def summary(profile):
    account = account_for(profile)
    pending = account.payments.filter(status=Payment.Status.PENDING, method=Payment.Method.BARIDIMOB).first()
    pending_card = account.payments.filter(status=Payment.Status.PENDING, method=Payment.Method.CARD).first()
    last = account.payments.exclude(status=Payment.Status.PENDING).first()
    return {
        "card_enabled": chargily.enabled(),
        "pending_card_id": pending_card.pk if pending_card else None,
        "free_points": account.free_points,
        "points_due": account.points_due,
        "amount_due_da": account.amount_due_da,
        "block_at": settings.POINTS_BLOCK_AT,
        "blocked": account.blocked,
        "points_per_contact": settings.POINTS_PER_CONTACT,
        "point_value_da": settings.POINT_VALUE_DA,
        "baridimob": {"rip": settings.BARIDIMOB_RIP, "name": settings.BARIDIMOB_NAME},
        "pending_payment": _payment_json(pending) if pending else None,
        "last_payment": _payment_json(last) if last else None,
        "history": [
            {
                "kind": e.kind,
                "label": e.get_kind_display(),
                "free_used": e.free_used,
                "due_delta": e.due_delta,
                "note": e.note,
                "created_at": e.created_at,
            }
            for e in account.entries.all()[:30]
        ],
    }


def _payment_json(p):
    return {
        "id": p.id, "method": p.method, "amount_da": p.amount_da, "points": p.points, "reference": p.reference,
        "status": p.status, "admin_note": p.admin_note, "created_at": p.created_at,
    }
