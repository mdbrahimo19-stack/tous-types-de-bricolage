from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path

from apps.accounts.views import privacy_policy


def health(_request):
    return JsonResponse({"status": "ok"})


def home(_request):
    """Page d'accueil du serveur (au lieu d'un « 404 » déroutant) : confirme qu'il fonctionne."""
    return HttpResponse(
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'><title>Serveur BRICOOL</title></head>"
        "<body style='margin:0;font-family:system-ui,sans-serif;background:#FAF7F3;color:#1F1A17'>"
        "<div style='max-width:520px;margin:0 auto;padding:48px 20px;text-align:center'>"
        "<h1 style='color:#0E7A55'>Serveur BRICOOL en marche ✔</h1>"
        "<p style='font-size:17px;line-height:1.5'>Le téléphone joint bien le serveur.<br>"
        "Recopiez cette adresse dans l'application : <strong>Profil → Serveur</strong>.</p>"
        "<p style='font-size:17px;line-height:1.6' dir='rtl'>الهاتف متصل بالخادم. انسخ هذا العنوان في التطبيق: "
        "<strong>الملف ← الخادم</strong>.</p>"
        "</div></body></html>"
    )


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("api/health/", health),
    # page publique (liens depuis les deux apps et la fiche Play Store)
    path("confidentialite/", privacy_policy, name="privacy-policy"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.catalog.urls")),
    path("api/", include("apps.locations.urls")),
    path("api/", include("apps.marketplace.urls")),
    path("api/", include("apps.billing.urls")),
    path("api/ai/", include("apps.ai.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
