"""Passe en EXPIRED les demandes publiées non attribuées arrivées à échéance (RG-02).

À planifier via cron (toutes les heures) en attendant Celery :
    */30 * * * *  cd /app && .venv/bin/python manage.py expire_requests
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.marketplace.models import ServiceRequest


class Command(BaseCommand):
    help = "Expire les demandes publiées/à devis dont expires_at est dépassé."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="N'écrit rien, affiche seulement.")

    def handle(self, *args, **options):
        now = timezone.now()
        qs = ServiceRequest.objects.filter(
            status__in=[ServiceRequest.Status.PUBLISHED, ServiceRequest.Status.QUOTES_RECEIVED],
            expires_at__lt=now,
        )
        count = qs.count()
        if options["dry_run"]:
            self.stdout.write(f"[dry-run] {count} demande(s) seraient expirées.")
            return
        updated = qs.update(status=ServiceRequest.Status.EXPIRED, updated_at=now)
        self.stdout.write(self.style.SUCCESS(f"{updated} demande(s) expirée(s)."))
