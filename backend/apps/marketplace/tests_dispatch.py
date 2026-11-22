"""Envoi des demandes aux bricoleurs les plus proches (GPS), par vagues."""
from datetime import timedelta
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import ProviderProfile
from apps.catalog.models import Category, ProviderCategory
from apps.locations.models import Commune, Wilaya

from .dispatch import advance_due_waves, ranked_providers, send_wave
from .models import Notification, RequestDispatch, ServiceRequest
from .tests import make_provider, make_user

CLIENT_LAT, CLIENT_LNG = 36.72, 3.09  # Kouba (Alger)
NO_THROTTLE = {"DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}}


def _north_of_client(km):
    """Coordonnées à ~`km` km au nord du client (1° de latitude ≈ 111 km)."""
    return f"{CLIENT_LAT + km / 111.0:.6f}", f"{CLIENT_LNG:.6f}"


@override_settings(REST_FRAMEWORK=NO_THROTTLE, DISPATCH_BATCH_SIZE=5, DISPATCH_WAVE_MINUTES=15,
                   DISPATCH_MAX_WAVES=4)
class DispatchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.wilaya = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        cls.kouba = Commune.objects.create(wilaya=cls.wilaya, name_fr="Kouba")
        cls.rouiba = Commune.objects.create(wilaya=cls.wilaya, name_fr="Rouiba")
        cls.plomberie = Category.objects.create(name_fr="Plomberie", order=1)
        cls.fuite = Category.objects.create(name_fr="Recherche de fuite", parent=cls.plomberie, order=1)
        cls.peinture = Category.objects.create(name_fr="Peinture", order=2)

    def setUp(self):
        cache.clear()
        self.client_user = make_user(phone="+213661000500")
        self.cc = APIClient()
        self.cc.force_authenticate(self.client_user)

    # ---------------------------------------------------------------- helpers
    def _pro(self, phone, km, *, category=None, communes=(), **fields):
        lat, lng = _north_of_client(km) if km is not None else (None, None)
        user, profile = make_provider(phone, category or self.plomberie, list(communes), lat=lat, lng=lng)
        if fields:
            for k, v in fields.items():
                setattr(profile, k, v)
            profile.save()
        return user, profile

    def _publish(self, category=None, gps=True, **over):
        payload = {
            "category": (category or self.plomberie).id,
            "title": "Fuite sous l'évier",
            "description": "Goutte à goutte.",
            "wilaya": self.wilaya.id,
            "commune": self.kouba.id,
            "urgency": "today",
            "publish_now": True,
        }
        if gps:
            payload.update(latitude=CLIENT_LAT, longitude=CLIENT_LNG)
        payload.update(over)
        resp = self.cc.post("/api/requests/", payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp, ServiceRequest.objects.get(pk=resp.data["id"])

    def _sent_to(self, req):
        return set(RequestDispatch.objects.filter(request=req).values_list("provider_id", flat=True))

    # ------------------------------------------------------------------ tests
    def test_first_wave_goes_to_the_five_nearest(self):
        pros = [self._pro(f"+21377000010{i}", km=1.1 * i) for i in range(1, 8)]  # 1,1 km … 7,7 km
        resp, req = self._publish()

        self.assertEqual(resp.data["dispatched_count"], 5)
        self.assertEqual(self._sent_to(req), {p.id for _, p in pros[:5]})
        self.assertEqual(
            Notification.objects.filter(type="request_nearby", data__request_id=req.id).count(), 5
        )

        nearest = APIClient(); nearest.force_authenticate(pros[0][0])
        feed = nearest.get("/api/feed/").data
        self.assertEqual(feed["count"], 1)
        self.assertAlmostEqual(feed["results"][0]["distance_km"], 1.1, delta=0.1)

        sixth = APIClient(); sixth.force_authenticate(pros[5][0])
        self.assertEqual(sixth.get("/api/feed/").data["count"], 0)
        quote = sixth.post("/api/quotes/", {"request": req.id, "amount": "3000", "lead_time_days": 1},
                           format="json")
        self.assertEqual(quote.status_code, 400)

    def test_next_wave_after_delay_without_quote(self):
        pros = [self._pro(f"+21377000020{i}", km=1.1 * i) for i in range(1, 8)]
        _, req = self._publish()
        now = timezone.now()

        self.assertEqual(advance_due_waves(now=now + timedelta(minutes=5)), 0)   # trop tôt
        self.assertEqual(advance_due_waves(now=now + timedelta(minutes=16)), 2)  # les 2 suivants
        wave2 = RequestDispatch.objects.filter(request=req, wave=2).values_list("provider_id", flat=True)
        self.assertEqual(set(wave2), {pros[5][1].id, pros[6][1].id})
        self.assertEqual(advance_due_waves(now=now + timedelta(minutes=40)), 0)  # plus personne

    def test_no_next_wave_once_a_quote_arrived(self):
        pros = [self._pro(f"+21377000030{i}", km=1.1 * i) for i in range(1, 8)]
        _, req = self._publish()
        pc = APIClient(); pc.force_authenticate(pros[0][0])
        q = pc.post("/api/quotes/", {"request": req.id, "amount": "3000", "lead_time_days": 1}, format="json")
        self.assertEqual(q.status_code, 201, q.content)
        self.assertEqual(advance_due_waves(now=timezone.now() + timedelta(minutes=16)), 0)

    @override_settings(DISPATCH_MAX_WAVES=1)
    def test_waves_are_capped(self):
        for i in range(1, 8):
            self._pro(f"+21377000040{i}", km=1.1 * i)
        self._publish()
        self.assertEqual(advance_due_waves(now=timezone.now() + timedelta(minutes=16)), 0)

    def test_eligibility_rules(self):
        _, ok = self._pro("+213770000501", km=3)
        _, family = self._pro("+213770000502", km=4)                        # fait toute la plomberie
        _, too_far = self._pro("+213770000503", km=8, radius_km=5)          # hors de son rayon
        self._pro("+213770000504", km=1, is_available=False)                # indisponible
        self._pro("+213770000505", km=1, verification_status="pending")     # non validé
        self._pro("+213770000506", km=1, category=self.peinture)            # autre métier
        _, req = self._publish(category=self.fuite)  # sous-catégorie de Plomberie

        self.assertEqual(self._sent_to(req), {ok.id, family.id})
        self.assertNotIn(too_far.id, self._sent_to(req))

    def test_client_is_never_sent_own_request(self):
        self.client_user.is_provider = True
        self.client_user.save()
        me = ProviderProfile.objects.create(
            user=self.client_user, verification_status="approved",
            latitude=CLIENT_LAT, longitude=CLIENT_LNG,
        )
        ProviderCategory.objects.create(provider=me, category=self.plomberie)
        _, req = self._publish()
        self.assertNotIn(me.id, self._sent_to(req))

    def test_commune_fallback_without_gps(self):
        _, local = self._pro("+213770000601", km=None, communes=[self.kouba])
        _, elsewhere = self._pro("+213770000602", km=None, communes=[self.rouiba])
        _, gps_pro = self._pro("+213770000603", km=2)
        _, req = self._publish(gps=False)

        self.assertEqual(self._sent_to(req), {local.id})
        self.assertIsNone(RequestDispatch.objects.get(request=req, provider=local).distance_km)
        self.assertNotIn(gps_pro.id, self._sent_to(req))
        self.assertNotIn(elsewhere.id, self._sent_to(req))

    def test_gps_pros_ranked_before_commune_only_pros(self):
        _, commune_only = self._pro("+213770000701", km=None, communes=[self.kouba])
        _, gps_far = self._pro("+213770000702", km=9)
        _, gps_near = self._pro("+213770000703", km=2)
        req = ServiceRequest.objects.create(
            client=self.client_user, category=self.plomberie, title="T", description="d",
            wilaya=self.wilaya, commune=self.kouba, latitude=CLIENT_LAT, longitude=CLIENT_LNG,
        )
        req.publish()
        self.assertEqual([p.id for p, _ in ranked_providers(req)], [gps_near.id, gps_far.id, commune_only.id])

    def test_client_notified_when_nobody_nearby(self):
        resp, req = self._publish()
        self.assertEqual(resp.data["dispatched_count"], 0)
        self.assertTrue(
            Notification.objects.filter(recipient=self.client_user, type="request_no_provider").exists()
        )
        # un bricoleur se libère : il reçoit la demande à la vague suivante
        _, pro = self._pro("+213770000801", km=2)
        self.assertEqual(advance_due_waves(now=timezone.now() + timedelta(minutes=16)), 1)
        self.assertEqual(self._sent_to(req), {pro.id})

    def test_gps_coordinates_are_validated(self):
        base = {
            "category": self.plomberie.id, "title": "T", "description": "d",
            "wilaya": self.wilaya.id, "commune": self.kouba.id,
        }
        only_lat = self.cc.post("/api/requests/", {**base, "latitude": 36.7}, format="json")
        self.assertEqual(only_lat.status_code, 400)
        bad = self.cc.post("/api/requests/", {**base, "latitude": 200, "longitude": 3}, format="json")
        self.assertEqual(bad.status_code, 400)
        ok = self.cc.post("/api/requests/", {**base, "latitude": 36.7538216, "longitude": 3.0587561},
                          format="json")
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(ok.data["latitude"], "36.753822")

    def test_feed_sorted_by_distance(self):
        pro_user, _ = self._pro("+213770000901", km=0)
        _, far = self._publish(title="Loin", latitude=f"{CLIENT_LAT + 5 / 111.0:.6f}", longitude=CLIENT_LNG)
        _, near = self._publish(title="Près")
        pc = APIClient(); pc.force_authenticate(pro_user)
        ids = [r["id"] for r in pc.get("/api/feed/").data["results"]]
        self.assertEqual(ids, [near.id, far.id])

    def test_republish_after_expiry_starts_again(self):
        self._pro("+213770001001", km=2)
        _, req = self._publish()
        req.status = ServiceRequest.Status.EXPIRED
        req.save()
        resp = self.cc.post(f"/api/requests/{req.id}/publish/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["dispatched_count"], 1)
        self.assertEqual(RequestDispatch.objects.get(request=req).wave, 1)

    def test_send_wave_ignores_closed_requests(self):
        self._pro("+213770001101", km=2)
        _, req = self._publish()
        RequestDispatch.objects.filter(request=req).delete()
        req.status = ServiceRequest.Status.CANCELLED
        req.save()
        self.assertEqual(send_wave(req), 0)

    def test_management_command(self):
        out = StringIO()
        call_command("dispatch_requests", stdout=out)
        self.assertIn("envoi", out.getvalue())
