from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.catalog.models import Category
from apps.locations.models import Commune, Wilaya
from apps.marketplace.models import Notification, ServiceRequest

from .tests import make_provider, make_user

# mêmes réglages DRF (pagination, etc.) mais sans limitation de débit
DRF_NO_THROTTLE = {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}}


@override_settings(REST_FRAMEWORK=DRF_NO_THROTTLE)
class TargetedRequestTests(TestCase):
    """Demande de devis adressée à un seul professionnel (depuis l'annuaire)."""

    @classmethod
    def setUpTestData(cls):
        alger = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        oran = Wilaya.objects.create(code="31", name_fr="Oran", is_active=True)
        cls.kouba = Commune.objects.create(wilaya=alger, name_fr="Kouba")
        cls.bir_el_djir = Commune.objects.create(wilaya=oran, name_fr="Bir El Djir")
        cls.alger = alger
        cls.plomberie = Category.objects.create(name_fr="Plomberie", order=1)
        cls.peinture = Category.objects.create(name_fr="Peinture", order=2)

        cls.client_user = make_user("+213661000201")
        cls.target_user, cls.target = make_provider("+213661000202", cls.plomberie, [cls.kouba])
        cls.other_user, cls.other = make_provider("+213661000203", cls.plomberie, [cls.kouba])
        # plombier d'Oran : hors de la zone du client
        cls.far_user, cls.far = make_provider("+213661000204", cls.plomberie, [cls.bir_el_djir])
        cls.pending_user, cls.pending = make_provider(
            "+213661000205", cls.plomberie, [cls.kouba], verified=False
        )

    def setUp(self):
        cache.clear()
        self.cc = self._client(self.client_user)

    @staticmethod
    def _client(user):
        c = APIClient()
        c.force_authenticate(user)
        return c

    def _create(self, target=None, category=None):
        payload = {
            "category": (category or self.plomberie).id,
            "title": "Fuite sous l'évier",
            "description": "Le siphon fuit depuis hier.",
            "wilaya": self.alger.id,
            "commune": self.kouba.id,
            "publish_now": True,
        }
        if target is not None:
            payload["target_provider"] = target.id
        return self.cc.post("/api/requests/", payload, format="json")

    def _feed_ids(self, user):
        resp = self._client(user).get("/api/feed/")
        self.assertEqual(resp.status_code, 200, resp.data)
        return [r["id"] for r in resp.data["results"]]

    def _quote(self, user, request_id):
        return self._client(user).post(
            "/api/quotes/", {"request": request_id, "amount": 3000, "lead_time_days": 1}, format="json"
        )

    def test_targeted_request_only_visible_to_target(self):
        rid = self._create(target=self.target).data["id"]
        self.assertIn(rid, self._feed_ids(self.target_user))
        self.assertNotIn(rid, self._feed_ids(self.other_user))

    def test_only_target_can_quote(self):
        rid = self._create(target=self.target).data["id"]
        refused = self._quote(self.other_user, rid)
        self.assertEqual(refused.status_code, 400)
        self.assertIn("réservée", str(refused.data))
        self.assertEqual(self._quote(self.target_user, rid).status_code, 201)

    def test_target_outside_usual_zone_can_still_answer(self):
        rid = self._create(target=self.far).data["id"]
        self.assertIn(rid, self._feed_ids(self.far_user))
        self.assertEqual(self._quote(self.far_user, rid).status_code, 201)

    def test_target_is_notified_on_publish(self):
        self._create(target=self.target)
        self.assertTrue(
            Notification.objects.filter(recipient=self.target_user, type="request_targeted").exists()
        )
        self.assertFalse(Notification.objects.filter(recipient=self.other_user).exists())

    def test_detail_shows_target_name(self):
        data = self._create(target=self.target).data
        self.assertEqual(data["target_provider"], self.target.id)
        self.assertEqual(data["target_provider_detail"]["id"], self.target.id)

    def test_open_to_all(self):
        rid = self._create(target=self.target).data["id"]
        resp = self.cc.post(f"/api/requests/{rid}/open_to_all/")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIsNone(resp.data["target_provider"])
        self.assertIn(rid, self._feed_ids(self.other_user))
        # une seconde fois : déjà ouverte
        self.assertEqual(self.cc.post(f"/api/requests/{rid}/open_to_all/").status_code, 400)

    def test_untargeted_request_unchanged(self):
        rid = self._create().data["id"]
        self.assertIn(rid, self._feed_ids(self.target_user))
        self.assertIn(rid, self._feed_ids(self.other_user))
        self.assertNotIn(rid, self._feed_ids(self.far_user))  # hors zone

    def test_rejects_provider_without_this_trade(self):
        resp = self._create(target=self.target, category=self.peinture)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("target_provider", resp.data)
        self.assertFalse(ServiceRequest.objects.exists())

    def test_rejects_unverified_provider(self):
        resp = self._create(target=self.pending)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("target_provider", resp.data)
