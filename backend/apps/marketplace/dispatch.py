"""Envoi d'une demande aux bricoleurs les plus proches (GPS), par vagues.

1re vague : les DISPATCH_BATCH_SIZE bricoleurs disponibles les plus proches.
Sans aucun devis au bout de DISPATCH_WAVE_MINUTES, la demande passe aux suivants
(au plus DISPATCH_MAX_WAVES vagues). Seuls les bricoleurs ayant reçu la demande
la voient dans leur fil et peuvent envoyer un devis.

Un bricoleur est éligible s'il est validé, disponible, fait ce métier (ou la famille
de ce métier) et si le client est dans son rayon de déplacement. Sans position GPS
(d'un côté ou de l'autre), on se rabat sur ses communes d'intervention.
"""
from datetime import timedelta
from decimal import Decimal
from math import cos, radians

from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone

from apps.accounts.models import ProviderProfile
from apps.locations.geo import haversine_km

from .models import RequestDispatch, ServiceRequest
from .notifications import notify

# Boîte de pré-filtrage autour du client ; le rayon d'un bricoleur est plafonné à 100 km.
MAX_SEARCH_KM = 100


def _has_gps(obj):
    return obj.latitude is not None and obj.longitude is not None


def _candidates(req):
    """Bricoleurs validés et disponibles, du bon métier, pas encore sollicités pour cette demande."""
    trade = Q(categories__category_id=req.category_id)
    if req.category.parent_id:
        trade |= Q(categories__category_id=req.category.parent_id)

    zone = Q(service_communes__id=req.commune_id)
    if _has_gps(req):
        lat, lng = float(req.latitude), float(req.longitude)
        dlat = MAX_SEARCH_KM / 111.0
        dlng = MAX_SEARCH_KM / (111.0 * max(cos(radians(lat)), 0.1))
        zone |= Q(latitude__range=(lat - dlat, lat + dlat), longitude__range=(lng - dlng, lng + dlng))

    return (
        ProviderProfile.objects.filter(
            trade, zone,
            verification_status=ProviderProfile.Verification.APPROVED,
            is_available=True,
            user__is_active=True,
        )
        .exclude(user_id=req.client_id)
        .exclude(dispatches__request=req)
        .exclude(points__points_due__gte=settings.POINTS_BLOCK_AT)  # compte bloqué (paiement à faire)
        .select_related("user")
        .distinct()
    )


def ranked_providers(req):
    """[(profil, distance_km | None)] du plus proche au plus loin ; sans GPS en dernier."""
    candidates = list(_candidates(req))
    by_commune = set(
        ProviderProfile.objects.filter(
            id__in=[p.id for p in candidates], service_communes__id=req.commune_id
        ).values_list("id", flat=True)
    )
    ranked = []
    for p in candidates:
        d = haversine_km(req.latitude, req.longitude, p.latitude, p.longitude)
        in_radius = d is not None and d <= p.radius_km
        if in_radius or p.id in by_commune:
            ranked.append((p, d))
    ranked.sort(key=lambda t: (
        t[1] is None, t[1] or 0, -float(t[0].rating_avg), -t[0].missions_count, t[0].id,
    ))
    return ranked


def send_wave(req, *, now=None):
    """Envoie la demande aux bricoleurs suivants les plus proches. Renvoie le nombre d'envois."""
    if req.status not in (ServiceRequest.Status.PUBLISHED, ServiceRequest.Status.QUOTES_RECEIVED):
        return 0
    wave = (req.dispatches.aggregate(m=Max("wave"))["m"] or 0) + 1
    if wave > settings.DISPATCH_MAX_WAVES:
        return 0
    chosen = ranked_providers(req)[: settings.DISPATCH_BATCH_SIZE]
    if not chosen:
        return 0

    now = now or timezone.now()
    RequestDispatch.objects.bulk_create(
        [
            RequestDispatch(
                request=req, provider=p, wave=wave, sent_at=now,
                distance_km=Decimal(str(d)) if d is not None else None,
            )
            for p, d in chosen
        ],
        ignore_conflicts=True,
    )
    category = req.category.name_fr
    for p, d in chosen:
        where = f"à {d:.1f} km".replace(".", ",") if d is not None else f"à {req.commune.name_fr}"
        notify(
            p.user, "request_nearby", "Nouvelle demande près de vous",
            f"{category} {where} : « {req.title} ».",
            data={"request_id": req.id},
        )
    return len(chosen)


def advance_due_waves(*, now=None):
    """Passe aux bricoleurs suivants pour les demandes restées sans devis. Renvoie le nombre d'envois."""
    now = now or timezone.now()
    cutoff = now - timedelta(minutes=settings.DISPATCH_WAVE_MINUTES)
    due = (
        ServiceRequest.objects.filter(status=ServiceRequest.Status.PUBLISHED, published_at__lte=cutoff)
        .annotate(last_sent=Max("dispatches__sent_at"), last_wave=Max("dispatches__wave"))
        .filter(Q(last_sent__isnull=True) | Q(last_sent__lte=cutoff))
        .filter(Q(last_wave__isnull=True) | Q(last_wave__lt=settings.DISPATCH_MAX_WAVES))
        .select_related("category", "commune")
    )
    return sum(send_wave(req, now=now) for req in due)
