"""Recalcul de la réputation d'un prestataire (MVP : note moyenne + compteurs)."""
from django.db.models import Avg, Count

from .models import Mission, Review


def recompute_provider_reputation(provider_user):
    profile = getattr(provider_user, "provider_profile", None)
    if profile is None:
        return

    agg = (
        Review.objects.filter(target=provider_user, moderation_status=Review.Moderation.APPROVED)
        .aggregate(avg=Avg("rating"), n=Count("id"))
    )
    profile.rating_avg = round(agg["avg"], 2) if agg["avg"] is not None else 0
    profile.reviews_count = agg["n"]
    profile.missions_count = Mission.objects.filter(
        provider=provider_user,
        status__in=[Mission.Status.COMPLETED, Mission.Status.PAID],
    ).count()
    profile.save(update_fields=["rating_avg", "reviews_count", "missions_count"])
