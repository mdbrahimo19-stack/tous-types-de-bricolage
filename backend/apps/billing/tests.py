"""Points des bricoleurs : 25 points par client, 50 offerts, blocage à 200 dus, paiement BaridiMob."""
from io import BytesIO

from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category
from apps.dashboard.stats import build_dashboard
from apps.locations.models import Commune, Wilaya
from apps.marketplace.dispatch import send_wave
from apps.marketplace.models import ServiceRequest
from apps.marketplace.tests import make_provider, make_user

from . import services
from .models import Payment, PointEntry, PointsAccount

SETTINGS = dict(
    REST_FRAMEWORK={"DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}},
    POINTS_PER_CONTACT=25, POINT_VALUE_DA=10, POINTS_WELCOME_FREE=50, POINTS_BLOCK_AT=200,
    BARIDIMOB_RIP="00799999000000000000", BARIDIMOB_NAME="TTB",
    PAYMENTS_NOTIFY_EMAIL="admin@example.com",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)


def _png():
    buf = BytesIO()
    Image.new("RGB", (20, 20), "white").save(buf, format="PNG")
    return SimpleUploadedFile("baridimob.png", buf.getvalue(), content_type="image/png")


@override_settings(**SETTINGS)
class PointsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.wilaya = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        cls.kouba = Commune.objects.create(wilaya=cls.wilaya, name_fr="Kouba")
        cls.plomberie = Category.objects.create(name_fr="Plomberie", order=1)

    def setUp(self):
        cache.clear()
        self.pro_user, self.profile = make_provider("+213770100100", self.plomberie, [self.kouba])
        self.pc = APIClient()
        self.pc.force_authenticate(self.pro_user)
        self.n = 0

    def _client_accepts(self):
        """Un nouveau client publie, le bricoleur envoie un devis, le client l'accepte."""
        self.n += 1
        client = make_user(phone=f"+2136610{self.n:05d}")
        cc = APIClient()
        cc.force_authenticate(client)
        req = ServiceRequest.objects.create(
            client=client, category=self.plomberie, title=f"Fuite {self.n}", description="d",
            wilaya=self.wilaya, commune=self.kouba,
        )
        req.publish()
        send_wave(req)
        q = self.pc.post("/api/quotes/", {"request": req.id, "amount": "3000", "lead_time_days": 1}, format="json")
        if q.status_code != 201:
            return q
        return cc.post(f"/api/quotes/{q.data['id']}/accept/")

    def _account(self):
        return PointsAccount.objects.get(provider=self.profile)

    def _owe(self, points):
        acc = services.account_for(self.profile)
        acc.free_points, acc.points_due = 0, points
        acc.save()

    def test_free_points_first_then_points_due(self):
        self.assertEqual(self._client_accepts().status_code, 201)
        self.assertEqual((self._account().free_points, self._account().points_due), (25, 0))
        self._client_accepts()
        self.assertEqual((self._account().free_points, self._account().points_due), (0, 0))
        self._client_accepts()
        self.assertEqual((self._account().free_points, self._account().points_due), (0, 25))
        self.assertEqual(PointEntry.objects.filter(kind="contact").count(), 3)

    def test_blocked_after_250_points_then_unblocked_by_admin(self):
        # 2 contacts offerts (50 pts) + 8 contacts payants (200 pts) = 250 points -> bloqué
        for _ in range(10):
            self.assertEqual(self._client_accepts().status_code, 201)
        acc = self._account()
        self.assertTrue(acc.blocked)
        self.assertEqual(acc.amount_due_da, 2000)
        self.assertTrue(self.pro_user.notifications.filter(type="account_blocked").exists())

        # bloqué : la demande suivante ne lui est pas envoyée et il ne peut pas répondre
        blocked = self._client_accepts()
        self.assertEqual(blocked.status_code, 403)
        self.assertIn("BaridiMob", str(blocked.data))
        self.assertFalse(ServiceRequest.objects.latest("id").dispatches.filter(provider=self.profile).exists())

        # il paie par BaridiMob et envoie la capture
        resp = self.pc.post("/api/provider/payments/", {"screenshot": _png(), "reference": "BM-123"},
                            format="multipart")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["amount_da"], 2000)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("2 000 DA", mail.outbox[0].subject)
        self.assertIn("/admin/billing/payment/", mail.outbox[0].body)
        # un seul paiement en attente à la fois
        again = self.pc.post("/api/provider/payments/", {"screenshot": _png()}, format="multipart")
        self.assertEqual(again.status_code, 400)

        # vous validez dans l'admin -> compte débloqué
        admin_user = User.objects.create_superuser(phone="+213550000001", password="x")
        services.approve_payment(Payment.objects.get(), by=admin_user)
        acc = self._account()
        self.assertEqual(acc.points_due, 0)
        self.assertFalse(acc.blocked)
        self.assertTrue(self.pro_user.notifications.filter(type="payment_approved").exists())
        self.assertEqual(self._client_accepts().status_code, 201)

    def test_rejected_payment_keeps_account_blocked(self):
        self._owe(200)
        self.pc.post("/api/provider/payments/", {"screenshot": _png()}, format="multipart")
        services.reject_payment(Payment.objects.get(), note="Aucun virement reçu.")
        self.assertTrue(self._account().blocked)
        self.assertIn("Aucun virement", self.pro_user.notifications.get(type="payment_rejected").body)
        # il peut renvoyer une capture
        resp = self.pc.post("/api/provider/payments/", {"screenshot": _png()}, format="multipart")
        self.assertEqual(resp.status_code, 201)

    def test_nothing_to_pay_and_screenshot_required(self):
        resp = self.pc.post("/api/provider/payments/", {"screenshot": _png()}, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self._owe(25)
        self.assertEqual(self.pc.post("/api/provider/payments/", {}, format="multipart").status_code, 400)

    def test_points_summary(self):
        self._client_accepts()
        data = self.pc.get("/api/provider/points/").data
        self.assertEqual(data["free_points"], 25)
        self.assertEqual(data["points_due"], 0)
        self.assertFalse(data["blocked"])
        self.assertEqual(data["block_at"], 200)
        self.assertEqual(data["baridimob"]["rip"], "00799999000000000000")
        self.assertEqual(len(data["history"]), 1)
        client_only = APIClient()
        client_only.force_authenticate(make_user(phone="+213661999999"))
        self.assertEqual(client_only.get("/api/provider/points/").status_code, 403)

    def test_charge_is_idempotent(self):
        self._client_accepts()
        mission = PointEntry.objects.get().mission
        services.charge_contact(self.profile, mission)
        self.assertEqual(PointEntry.objects.count(), 1)

    def test_dashboard_lists_pending_payment(self):
        self._owe(200)
        self.pc.post("/api/provider/payments/", {"screenshot": _png()}, format="multipart")
        todo = {s["title"]: s for s in build_dashboard()["ttb_todo"]}
        self.assertEqual(todo["Paiements BaridiMob à vérifier"]["count"], 1)

    def test_admin_approve_action(self):
        self._owe(200)
        self.pc.post("/api/provider/payments/", {"screenshot": _png()}, format="multipart")
        admin_user = User.objects.create_superuser(phone="+213550000002", password="x")
        self.client.force_login(admin_user)
        self.assertEqual(self.client.get("/admin/billing/payment/").status_code, 200)
        self.assertEqual(self.client.get(f"/admin/billing/payment/{Payment.objects.get().pk}/change/").status_code, 200)
        resp = self.client.post("/admin/billing/payment/", {
            "action": "approve", "_selected_action": [Payment.objects.get().pk],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(self._account().blocked)
