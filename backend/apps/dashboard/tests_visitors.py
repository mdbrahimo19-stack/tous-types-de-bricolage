"""Visiteurs de l'application : enregistrement (une visite / personne / jour / app) et tableau de bord."""
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import DailyVisit, User

from .stats import build_dashboard


class VisitorsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser(phone="+213770000009", password="x")
        self.client_user = User.objects.create_user(phone="+213661000011", full_name="Sara")
        self.pro_user = User.objects.create_user(phone="+213661000012", full_name="Karim", is_provider=True)

    def _api(self, user, app):
        api = APIClient()
        api.force_authenticate(user)
        return api.get("/api/auth/me/", HTTP_X_APP=app)

    def test_visit_recorded_once_per_day_and_app(self):
        self._api(self.client_user, "client")
        self._api(self.client_user, "client")  # même jour, même app : une seule ligne
        self._api(self.pro_user, "pro")
        self.assertEqual(DailyVisit.objects.filter(user=self.client_user).count(), 1)
        self.assertEqual(DailyVisit.objects.get(user=self.pro_user).app, "pro")
        self.client_user.refresh_from_db()
        self.assertIsNotNone(self.client_user.last_seen_at)

    def test_unknown_app_header_is_stored_as_other(self):
        self._api(self.client_user, "pirate")
        self.assertEqual(DailyVisit.objects.get(user=self.client_user).app, "")

    def test_anonymous_requests_are_not_counted(self):
        APIClient().get("/api/health/")
        APIClient().get("/api/auth/me/")
        self.assertEqual(DailyVisit.objects.count(), 0)

    def test_dashboard_counts_and_chart(self):
        today = timezone.localdate()
        DailyVisit.objects.create(user=self.client_user, day=today, app="client")
        DailyVisit.objects.create(user=self.pro_user, day=today, app="pro")
        DailyVisit.objects.create(user=self.client_user, day=today - timedelta(days=3), app="client")
        DailyVisit.objects.create(user=self.client_user, day=today - timedelta(days=40), app="client")  # hors 30 j

        v = build_dashboard()["ttb_visitors"]
        figures = {f["label"]: f["value"] for f in v["figures"]}
        self.assertEqual(figures["Visiteurs aujourd'hui"], 2)
        self.assertEqual(figures["Visiteurs (7 jours)"], 2)
        self.assertEqual(figures["Visiteurs (30 jours)"], 2)
        self.assertEqual(len(v["days"]), 30)
        last = v["days"][-1]
        self.assertEqual((last["client"], last["pro"], last["total"]), (1, 1, 2))
        self.assertEqual(v["max_visits"], 2)

    def test_admin_home_shows_visitors_section(self):
        self.client.force_login(self.admin)
        page = self.client.get("/admin/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Visiteurs de l")
        self.assertContains(page, "Nouveaux inscrits par jour")
