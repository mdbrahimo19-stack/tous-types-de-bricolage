from django.contrib.admin.apps import AdminConfig


class TTBAdminConfig(AdminConfig):
    """Remplace `django.contrib.admin` dans INSTALLED_APPS : même admin,
    mais sa page d'accueil devient le tableau de bord."""

    default_site = "apps.dashboard.site.TTBAdminSite"
