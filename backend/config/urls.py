from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from apps.accounts.views import landing, privacy_policy


def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("", landing, name="home"),  # site vitrine (français / arabe)
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
