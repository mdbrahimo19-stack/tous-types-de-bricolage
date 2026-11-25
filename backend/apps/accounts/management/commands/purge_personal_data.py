from django.core.management.base import BaseCommand

from apps.accounts import privacy


class Command(BaseCommand):
    help = (
        "Nettoyage des données personnelles (loi 18-07) : codes SMS de plus d'un jour, notifications "
        "de plus de 180 jours, anonymisation des comptes inactifs depuis PRIVACY_RETENTION_YEARS ans."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Compter sans rien effacer.")

    def handle(self, *args, **options):
        summary = privacy.purge(dry_run=options["dry_run"])
        prefix = "[essai] " if options["dry_run"] else ""
        self.stdout.write(
            f"{prefix}codes SMS : {summary['codes_sms']} · notifications : {summary['notifications']} · "
            f"comptes inactifs anonymisés : {summary['comptes_inactifs']}"
        )
