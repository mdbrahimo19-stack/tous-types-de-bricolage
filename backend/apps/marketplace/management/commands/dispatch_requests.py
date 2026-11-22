"""Envoie aux bricoleurs suivants les demandes restées sans devis (vague suivante).

À lancer toutes les 5 minutes (service `scheduler` de deploy/docker-compose.yml) :
    python manage.py dispatch_requests
"""
from django.core.management.base import BaseCommand

from apps.marketplace.dispatch import advance_due_waves


class Command(BaseCommand):
    help = "Élargit l'envoi des demandes sans devis aux bricoleurs suivants les plus proches."

    def handle(self, *args, **options):
        sent = advance_due_waves()
        self.stdout.write(self.style.SUCCESS(f"{sent} envoi(s) à de nouveaux bricoleurs."))
