from django.contrib.admin import AdminSite

from .stats import build_dashboard


class TTBAdminSite(AdminSite):
    site_header = "BRICOOL — Administration"
    site_title = "BRICOOL Admin"
    index_title = "Tableau de bord"
    index_template = "admin/ttb_dashboard.html"

    def index(self, request, extra_context=None):
        context = build_dashboard()
        context.update(extra_context or {})
        return super().index(request, extra_context=context)
