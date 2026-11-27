"""Calcul des chiffres affichés sur la page d'accueil de l'admin."""

from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone

from django.conf import settings

from apps.accounts.models import DailyVisit, ProviderProfile, User
from apps.billing.models import Payment, PointsAccount
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
    points = PointsAccount.objects.aggregate(
        due=Sum("points_due"),
        blocked=Count("id", filter=Q(points_due__gte=settings.POINTS_BLOCK_AT)),
    )
    cashed = Payment.objects.filter(status=Payment.Status.APPROVED).aggregate(total=Sum("amount_da"))

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
        {
            "label": "Points à encaisser",
            "value": _da((points["due"] or 0) * settings.POINT_VALUE_DA),
            "hint": f"{points['blocked']} bricoleur(s) bloqué(s)",
            "url": _changelist(PointsAccount),
        },
        {"label": "Encaissé (BaridiMob)", "value": _da(cashed["total"]), "url": _changelist(Payment)},
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
    pending_payments = (
        Payment.objects.filter(status=Payment.Status.PENDING)
        .select_related("account__provider__user")
        .order_by("created_at")
    )
    local = timezone.localtime

    return [
        _section(
            "Paiements BaridiMob à vérifier",
            pending_payments,
            lambda p: f"{_da(p.amount_da)} — {p.account.provider} · envoyé le {local(p.created_at):%d/%m %H:%M}",
            _changelist(Payment, status__exact="pending"),
            "Aucun paiement en attente.",
        ),
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


CHART_DAYS = 30


def _distinct_visitors(since, **filters):
    return DailyVisit.objects.filter(day__gte=since, **filters).values("user").distinct().count()


def visitors(now):
    """Fréquentation des deux applications : chiffres du jour / 7 j / 30 j et deux graphiques sur 30 jours."""
    today = timezone.localdate(now)
    start = today - timedelta(days=CHART_DAYS - 1)

    by_day = {}
    for row in (
        DailyVisit.objects.filter(day__gte=start)
        .values("day", "app")
        .annotate(n=Count("user", distinct=True))
    ):
        by_day.setdefault(row["day"], {})[row["app"]] = row["n"]
    signups = {
        row["d"]: row["n"]
        for row in User.objects.filter(date_joined__date__gte=start)
        .annotate(d=TruncDate("date_joined"))
        .values("d")
        .annotate(n=Count("id"))
    }

    days = []
    for i in range(CHART_DAYS):
        d = start + timedelta(days=i)
        counts = by_day.get(d, {})
        client, pro, other = counts.get("client", 0), counts.get("pro", 0), counts.get("", 0)
        days.append({
            "date": d, "client": client, "pro": pro, "other": other,
            "total": client + pro + other, "signups": signups.get(d, 0),
            "show_label": i % 5 == 0 or i == CHART_DAYS - 1,
        })
    max_visits = max((x["total"] for x in days), default=0) or 1
    max_signups = max((x["signups"] for x in days), default=0) or 1
    for x in days:
        x["client_pct"] = round(100 * x["client"] / max_visits, 1)
        x["pro_pct"] = round(100 * x["pro"] / max_visits, 1)
        x["other_pct"] = round(100 * x["other"] / max_visits, 1)
        x["signups_pct"] = round(100 * x["signups"] / max_signups, 1)

    week = today - timedelta(days=6)
    figures = [
        {
            "label": "Visiteurs aujourd'hui",
            "value": _distinct_visitors(today),
            "hint": f"{_distinct_visitors(today, app='client')} clients · {_distinct_visitors(today, app='pro')} artisans",
        },
        {"label": "Visiteurs (7 jours)", "value": _distinct_visitors(week)},
        {"label": "Visiteurs (30 jours)", "value": _distinct_visitors(start)},
        {"label": "Inscrits aujourd'hui", "value": signups.get(today, 0)},
    ]
    recent = User.objects.filter(last_seen_at__isnull=False).order_by("-last_seen_at")[:RECENT_LIMIT]
    return {
        "figures": [dict(f, url=_changelist(DailyVisit)) for f in figures],
        "days": days,
        "max_visits": max_visits if any(x["total"] for x in days) else 0,
        "max_signups": max_signups if any(x["signups"] for x in days) else 0,
        "has_other": any(x["other"] for x in days),
        "recent": [
            {"text": f"{u} — {u.phone}", "date": u.last_seen_at, "url": _change(u),
             "app": "Artisan" if u.is_provider else "Client"}
            for u in recent
        ],
        "list_url": _changelist(DailyVisit),
    }


def build_dashboard():
    now = timezone.now()
    return {
        "ttb_visitors": visitors(now),
        "ttb_figures": key_figures(now),
        "ttb_todo": todo(now),
        "ttb_recent": recent_activity(),
    }
