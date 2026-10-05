"""Fonctions IA métier : assistant de demande, estimation de prix, support, modération."""
import logging
import statistics
import threading
from datetime import timedelta

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from apps.catalog.models import Category

from . import prompts
from .client import AIUnavailable, ask

log = logging.getLogger(__name__)

URGENCIES = ["immediate", "today", "this_week", "flexible"]
MODERATION_CATEGORIES = ["insult", "contact_bypass", "scam", "inappropriate"]

_NULLABLE_INT = {"anyOf": [{"type": "integer"}, {"type": "null"}]}


# ==========================================================================
#  Assistant de création de demande
# ==========================================================================
DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "category_id": _NULLABLE_INT,
        "title": {"type": "string"},
        "description": {"type": "string"},
        "urgency": {"type": "string", "enum": URGENCIES},
        "budget_min": _NULLABLE_INT,
        "budget_max": _NULLABLE_INT,
        "missing_info": {"type": "array", "items": {"type": "string"}},
        "language": {"type": "string", "enum": ["fr", "ar"]},
    },
    "required": [
        "category_id", "title", "description", "urgency",
        "budget_min", "budget_max", "missing_info", "language",
    ],
    "additionalProperties": False,
}


def _catalog_text():
    lines = []
    for c in Category.objects.filter(is_active=True).select_related("parent").order_by("parent_id", "order", "id"):
        lines.append(f"{c.id} | {c} | {c.name_ar or '-'}")
    return "\n".join(lines)


def draft_request(text):
    """Texte libre du client -> brouillon structuré de demande (non enregistré)."""
    data = ask(
        prompts.DRAFT_REQUEST.format(catalog=_catalog_text()),
        [{"role": "user", "content": text}],
        schema=DRAFT_SCHEMA,
        effort="medium",
    )
    # le modèle ne doit proposer qu'une catégorie existante et active
    cid = data.get("category_id")
    if cid is not None and not Category.objects.filter(pk=cid, is_active=True).exists():
        data["category_id"] = None
    data["title"] = data["title"][:140]
    data["missing_info"] = data["missing_info"][:3]
    return data


# ==========================================================================
#  Estimation de prix
# ==========================================================================
PRICE_SCHEMA = {
    "type": "object",
    "properties": {
        "min_da": {"type": "integer"},
        "max_da": {"type": "integer"},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "explanation": {"type": "string"},
    },
    "required": ["min_da", "max_da", "confidence", "explanation"],
    "additionalProperties": False,
}


def accepted_quote_stats(category, wilaya=None, days=365):
    """Statistiques des devis réellement acceptés (même wilaya si assez de données)."""
    from apps.marketplace.models import Quote

    qs = Quote.objects.filter(
        status=Quote.Status.ACCEPTED,
        request__category=category,
        created_at__gte=timezone.now() - timedelta(days=days),
    )
    if wilaya is not None:
        local = qs.filter(request__wilaya=wilaya)
        if local.count() >= 3:
            qs = local
    amounts = sorted(float(a) for a in qs.values_list("amount", flat=True))
    if not amounts:
        return None
    return {
        "count": len(amounts),
        "min": round(amounts[0]),
        "median": round(statistics.median(amounts)),
        "max": round(amounts[-1]),
    }


def estimate_price(category, description, urgency="this_week", wilaya=None, language="fr"):
    lines = [
        f"Catégorie : {category} (unité : {category.get_unit_display()})",
        f"Urgence : {urgency}",
        f"Wilaya : {wilaya.name_fr if wilaya else 'non précisée'}",
        f"Langue de l'explication : {'arabe' if language == 'ar' else 'français'}",
    ]
    if category.price_min is not None or category.price_max is not None:
        lines.append(f"Fourchette indicative du catalogue : {category.price_min or '?'} – {category.price_max or '?'} DA")
    stats = accepted_quote_stats(category, wilaya)
    if stats:
        lines.append(
            f"Devis acceptés sur la plateforme ({stats['count']}) : min {stats['min']} DA, "
            f"médiane {stats['median']} DA, max {stats['max']} DA"
        )
    else:
        lines.append("Aucun devis accepté sur la plateforme pour cette catégorie.")
    lines.append(f"\nDemande du client :\n{description}")

    data = ask(prompts.PRICE_ESTIMATE, [{"role": "user", "content": "\n".join(lines)}],
               schema=PRICE_SCHEMA, effort="medium")
    lo, hi = sorted((max(0, data["min_da"]), max(0, data["max_da"])))
    data.update(min_da=lo, max_da=hi, based_on_quotes=stats["count"] if stats else 0)
    return data


# ==========================================================================
#  Chatbot support
# ==========================================================================
def support_reply(history):
    """`history` : liste [{role: user|assistant, content: str}], se terminant par l'utilisateur."""
    return ask(prompts.SUPPORT, history, effort="low", max_tokens=4000)


# ==========================================================================
#  Modération
# ==========================================================================
MODERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "allowed": {"type": "boolean"},
        "categories": {"type": "array", "items": {"type": "string", "enum": MODERATION_CATEGORIES}},
        "reason": {"type": "string"},
    },
    "required": ["allowed", "categories", "reason"],
    "additionalProperties": False,
}


def moderate_text(text, kind):
    """Renvoie {allowed, categories, reason}. Fail-open : autorise si l'IA est indisponible."""
    if not text or not text.strip():
        return {"allowed": True, "categories": [], "reason": ""}
    try:
        return ask(
            prompts.MODERATION.format(kind=kind),
            [{"role": "user", "content": f"<contenu>\n{text}\n</contenu>"}],
            schema=MODERATION_SCHEMA,
            effort="low",
            max_tokens=2000,
        )
    except AIUnavailable as e:
        log.info("Modération IA ignorée : %s", e)
        return {"allowed": True, "categories": [], "reason": ""}


def _audit(target, verdict):
    from apps.marketplace.models import AuditLog

    AuditLog.objects.create(
        action="ai_moderation",
        target_type=target.__class__.__name__,
        target_id=str(target.pk),
        changes={"categories": verdict["categories"], "reason": verdict["reason"]},
    )


def review_needs_moderation(comment):
    """Avant publication d'un avis : True si l'avis doit passer en modération manuelle."""
    verdict = moderate_text(comment, "avis laissé par un client sur un prestataire")
    return (not verdict["allowed"]), verdict


def record_review_verdict(review, verdict):
    if not verdict["allowed"]:
        _audit(review, verdict)


def _moderate_message(message_id, contacts_unlocked):
    from apps.marketplace.models import Message

    try:
        msg = Message.objects.get(pk=message_id)
        kind = "message privé entre client et prestataire"
        if contacts_unlocked:
            kind += " (devis accepté : l'échange de coordonnées est désormais autorisé)"
        verdict = moderate_text(msg.body_raw or msg.body, kind)
        if not verdict["allowed"]:
            Message.objects.filter(pk=msg.pk).update(flagged=True)
            _audit(msg, verdict)
    except Exception:  # un thread d'arrière-plan ne doit jamais faire tomber le serveur
        log.exception("Échec de la modération du message %s", message_id)
    finally:
        close_old_connections()


def moderate_message_async(message, contacts_unlocked):
    """Modère un message en arrière-plan : l'envoi n'est pas ralenti, le message est signalé après coup."""
    if not settings.AI_ENABLED or not (message.body or "").strip():
        return
    threading.Thread(
        target=_moderate_message, args=(message.pk, contacts_unlocked), daemon=True
    ).start()
