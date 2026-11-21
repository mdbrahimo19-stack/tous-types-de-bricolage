"""Calcul des chiffres affichés sur la page d'accueil de l'admin."""

from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import ProviderProfile, User
from apps.marketplace.models import AuditLog, Message, Mission, Quote, Review, ServiceRequest

RECENT_LIMIT = 8
DONE_MISSION_STATUSES = (Mission.Status.COMPLETED, Mission.Status.PAID)
ACTIVE_MISSION_STATUSES = (Mission.Status.PLANNED, Mission.Status.CONFIRMED, Mission.Status.IN_PROGRESS)
OPEN_REQUEST_STATUSES = (ServiceRequest.Status.PUBLISHED, ServiceRequest.Status.QUOTES_RECEIVED)


def _changelist(model, **filters):
    """URL de la liste admin d'un modèle, avec filtres facultatifs (?champ=valeur)."""
    url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
    if filters:
        url += "?" + "&".join(f"{k}={v}" for k, v in filters.items())
    return url


def _change(obj):
    return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])


def _da(amount):
    return f"{amount or 0:,.0f} DA".replace(",", " ")


def key_figures(now):
    week_ago = now - timedelta(days=7)
    users = User.objects.aggregate(
        clients=Count("id", filter=Q(is_client=True)),
        providers=Count("id", filter=Q(is_provider=True)),
        new_week=Count("id", filter=Q(date_joined__gte=week_ago)),
    )
    requests = ServiceRequest.objects.aggregate(
        total=Count("id", filter=~Q(status=ServiceRequest.Status.DRAFT)),
        open=Count("id", filter=Q(status__in=OPEN_REQUEST_STATUSES)),
        new_week=Count("id", filter=Q(published_at__gte=week_ago)),
    )
    quotes = Quote.objects.aggregate(
        total=Count("id"),
        accepted=Count("id", filter=Q(status=Quote.Status.ACCEPTED)),
    )
    missions = Mission.objects.aggregate(
        active=Count("id", filter=Q(status__in=ACTIVE_MISSION_STATUSES)),
        done=Count("id", filter=Q(status__in=DONE_MISSION_STATUSES)),
        amount=Sum("amount_due", filter=Q(status__in=DONE_MISSION_STATUSES)),
    )
    reviews = Review.objects.filter(moderation_status=Review.Moderation.APPROVED).aggregate(
        avg=Avg("rating"), n=Count("id")
    )
    acceptance = round(100 * quotes["accepted"] / quotes["total"]) if quotes["total"] else None

    return [
        {"label": "Clients", "value": users["clients"], "url": _changelist(User, is_client__exact=1)},
        {"label": "Prestataires", "value": users["providers"], "url": _changelist(ProviderProfile)},
        {"label": "Inscrits (7 jours)", "value": users["new_week"], "url": _changelist(User)},
        {"label": "Demandes publiées", "value": requests["total"], "url": _changelist(ServiceRequest)},
        {"label": "Demandes ouvertes", "value": requests["open"], "url": _changelist(ServiceRequest)},
        {"label": "Demandes (7 jours)", "value": requests["new_week"], "url": _changelist(ServiceRequest)},
        {
            "label": "Devis envoyés",
            "value": quotes["total"],
            "hint": f"{acceptance} % acceptés" if acceptance is not None else "",
            "url": _changelist(Quote),
        },
        {"label": "Missions en cours", "value": missions["active"], "url": _changelist(Mission)},
        {"label": "Missions terminées", "value": missions["done"], "url": _changelist(Mission)},
        {"label": "Montant des missions terminées", "value": _da(missions["amount"]), "url": _changelist(Mission)},
        {
            "label": "Note moyenne",
            "value": f"{reviews['avg']:.1f} ★" if reviews["avg"] is not None else "—",
            "hint": f"{reviews['n']} avis publiés",
            "url": _changelist(Review),
        },
    ]


def _section(title, qs, label, list_url, empty):
    return {
        "title": title,
        "count": qs.count(),
        "items": [{"text": label(o), "url": _change(o)} for o in qs[:RECENT_LIMIT]],
        "list_url": list_url,
        "empty": empty,
    }


def todo(now):
    pending_providers = (
        ProviderProfile.objects.filter(verification_status=ProviderProfile.Verification.PENDING)
        .select_related("user")
        .order_by("created_at")
    )
    flagged_messages = Message.objects.filter(flagged=True).select_related("sender").order_by("-created_at")
    pending_reviews = (
        Review.objects.filter(moderation_status=Review.Moderation.PENDING)
        .select_related("author", "target")
        .order_by("created_at")
    )
    no_quote = (
        ServiceRequest.objects.filter(
            status=ServiceRequest.Status.PUBLISHED,
            published_at__lte=now - timedelta(hours=24),
        )
        .annotate(n_quotes=Count("quotes"))
        .filter(n_quotes=0)
        .select_related("commune", "category")
        .order_by("published_at")
    )
    local = timezone.localtime

    return [
        _section(
            "Prestataires à vérifier",
            pending_providers,
            lambda p: f"{p} — {p.user.phone} · inscrit le {local(p.created_at):%d/%m}",
            _changelist(ProviderProfile, verification_status__exact="pending"),
            "Aucun prestataire en attente.",
        ),
        _section(
            "Messages signalés",
            flagged_messages,
            lambda m: f"{m.sender} : « {(m.body or '[photo]')[:60]} »",
            _changelist(Message, flagged__exact=1),
            "Aucun message signalé.",
        ),
        _section(
            "Avis à modérer",
            pending_reviews,
            lambda r: f"{r.rating}★ de {r.author} sur {r.target} : « {r.comment[:50]} »",
            _changelist(Review, moderation_status__exact="pending"),
            "Aucun avis en attente.",
        ),
        _section(
            "Demandes sans devis depuis plus de 24 h",
            no_quote,
            lambda r: f"{r.title} — {r.category} · {r.commune} · publiée le {local(r.published_at):%d/%m %H:%M}",
            _changelist(ServiceRequest, status__exact="published"),
            "Toutes les demandes de plus de 24 h ont reçu un devis.",
        ),
    ]


def recent_activity():
    requests = (
        ServiceRequest.objects.exclude(status=ServiceRequest.Status.DRAFT)
        .select_related("client", "commune")
        .order_by("-created_at")[:RECENT_LIMIT]
    )
    missions = Mission.objects.select_related("request", "provider").order_by("-updated_at")[:RECENT_LIMIT]
    logs = AuditLog.objects.select_related("actor").order_by("-created_at")[:RECENT_LIMIT]
    return [
        {
            "title": "Dernières demandes",
            "list_url": _changelist(ServiceRequest),
            "rows": [
                {
                    "text": f"{r.title} — {r.client} · {r.commune}",
                    "status": r.get_status_display(),
                    "date": r.created_at,
                    "url": _change(r),
                }
                for r in requests
            ],
        },
        {
            "title": "Dernières missions",
            "list_url": _changelist(Mission),
            "rows": [
                {
                    "text": f"{m.request.title} — {m.provider} · {_da(m.amount_due)}",
                    "status": m.get_status_display(),
                    "date": m.updated_at,
                    "url": _change(m),
                }
                for m in missions
            ],
        },
        {
            "title": "Journal des actions",
            "list_url": _changelist(AuditLog),
            "rows": [
                {
                    "text": f"{log.action} {log.target_type} {log.target_id}".strip(),
                    "status": str(log.actor) if log.actor else "système",
                    "date": log.created_at,
                    "url": _change(log),
                }
                for log in logs
            ],
        },
    ]


def build_dashboard():
    now = timezone.now()
    return {
        "ttb_figures": key_figures(now),
        "ttb_todo": todo(now),
        "ttb_recent": recent_activity(),
    }
