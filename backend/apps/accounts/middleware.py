"""Compte les visiteurs de l'application : au plus une écriture par personne, par jour et par app."""
import logging

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger("ttb.accounts")

APPS = {"client", "pro"}


class VisitMiddleware:
    """Après chaque requête d'un utilisateur connecté : note la visite du jour (DailyVisit).

    L'application envoie l'en-tête « X-App: client | pro ». Le cache évite d'écrire en base
    à chaque requête : une seule écriture par personne / jour / app."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._track(request)
        except Exception:  # les statistiques ne doivent jamais casser une requête
            logger.exception("Visite non enregistrée")
        return response

    def _track(self, request):
        if not request.path.startswith("/api/"):
            return
        user = getattr(request, "user", None)  # DRF recopie ici l'utilisateur authentifié par JWT
        if user is None or not user.is_authenticated:
            return
        app = (request.headers.get("X-App") or "").strip().lower()
        app = app if app in APPS else ""
        today = timezone.localdate()
        key = f"visit:{user.pk}:{today.isoformat()}:{app}"
        if not cache.add(key, 1, timeout=60 * 60 * 26):
            return  # déjà notée aujourd'hui pour cette app
        from .models import DailyVisit, User

        DailyVisit.objects.get_or_create(user_id=user.pk, day=today, app=app)
        User.objects.filter(pk=user.pk).update(last_seen_at=timezone.now())
