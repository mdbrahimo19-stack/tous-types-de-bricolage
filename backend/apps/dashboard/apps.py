from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Porte les templates du tableau de bord (pas de modèles)."""

    name = "apps.dashboard"
    label = "dashboard"
    verbose_name = "Tableau de bord"
