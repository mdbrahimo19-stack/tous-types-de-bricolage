"""Paiement des points par carte Edahabia / CIB (Chargily Pay), sans réseau : Chargily est simulé."""
import hashlib
import hmac
import json
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.catalog.models import Category
from apps.locations.models import Commune, Wilaya
from apps.marketplace.tests import make_provider

from . import chargily, services
from .models import Payment, PointsAccount

SECRET = "test_sk_secret_de_test"  # clé factice, jamais une vraie clé


def _signed(body: dict):
    raw = json.dumps(body).encode("utf-8")
    return raw, hmac.new(SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest()


@override_settings(CHARGILY_SECRET_KEY=SECRET, CHARGILY_MODE="test", PUBLIC_BASE_URL="")
class CardPaymentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        alger = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        cls.kouba = Commune.objects.create(wilaya=alger, name_fr="Kouba")
        cls.plomberie = Category.objects.create(name_fr="Plomberie", order=1)

    def setUp(self):
        cache.clear()
        self.user, self.profile = make_provider("+213770200200", self.plomberie, [self.kouba])
        self.account = services.account_for(self.profile)
        self.account.free_points = 0
        self.account.points_due = 200  # bloqué : 2 000 DA à payer
        self.account.save()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _start(self):
        with mock.patch.object(chargily, "create_checkout",
                               return_value={"id": "chk_123", "checkout_url": "https://pay.chargily.net/x"}) as m:
            resp = self.client.post("/api/provider/payments/card/")
        return resp, m

    def test_start_creates_card_payment_for_all_points_due(self):
        resp, create = self._start()
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["checkout_url"], "https://pay.chargily.net/x")
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs["amount_da"], 2000)
        self.assertIn("/api/billing/paiement-termine/?r=ok", kwargs["success_url"])
        self.assertEqual(kwargs["webhook_url"], "")  # pas d'adresse publique HTTPS en local
        payment = Payment.objects.get(pk=resp.data["payment_id"])
        self.assertEqual((payment.method, payment.status, payment.checkout_id), ("card", "pending", "chk_123"))

    def test_sync_paid_unblocks_account(self):
        resp, _ = self._start()
        pid = resp.data["payment_id"]
        with mock.patch.object(chargily, "retrieve_checkout", return_value={"status": "paid", "amount": 2000}):
            sync = self.client.post(f"/api/provider/payments/{pid}/sync/")
        self.assertEqual(sync.data["status"], "approved")
        self.account.refresh_from_db()
        self.assertEqual(self.account.points_due, 0)
        self.assertFalse(self.account.blocked)

    def test_sync_refuses_smaller_amount(self):
        resp, _ = self._start()
        pid = resp.data["payment_id"]
        with mock.patch.object(chargily, "retrieve_checkout", return_value={"status": "paid", "amount": 50}):
            self.client.post(f"/api/provider/payments/{pid}/sync/")
        self.assertEqual(Payment.objects.get(pk=pid).status, "pending")
        self.account.refresh_from_db()
        self.assertTrue(self.account.blocked)

    def test_sync_failed_closes_page_without_unblocking(self):
        resp, _ = self._start()
        pid = resp.data["payment_id"]
        with mock.patch.object(chargily, "retrieve_checkout", return_value={"status": "failed"}):
            sync = self.client.post(f"/api/provider/payments/{pid}/sync/")
        self.assertEqual(sync.data["status"], "rejected")
        self.account.refresh_from_db()
        self.assertTrue(self.account.blocked)

    def test_webhook_with_valid_signature_approves(self):
        resp, _ = self._start()
        raw, sig = _signed({"type": "checkout.paid", "data": {"id": "chk_123", "status": "paid", "amount": 2000}})
        hook = APIClient().post("/api/billing/chargily/webhook/", raw, content_type="application/json",
                                HTTP_SIGNATURE=sig)
        self.assertEqual(hook.status_code, 200)
        self.assertEqual(Payment.objects.get(pk=resp.data["payment_id"]).status, "approved")
        self.assertEqual(PointsAccount.objects.get(pk=self.account.pk).points_due, 0)

    def test_webhook_with_bad_signature_is_refused(self):
        resp, _ = self._start()
        raw, _ = _signed({"type": "checkout.paid", "data": {"id": "chk_123", "status": "paid", "amount": 2000}})
        hook = APIClient().post("/api/billing/chargily/webhook/", raw, content_type="application/json",
                                HTTP_SIGNATURE="faux")
        self.assertEqual(hook.status_code, 403)
        self.assertEqual(Payment.objects.get(pk=resp.data["payment_id"]).status, "pending")

    def test_other_provider_cannot_sync(self):
        resp, _ = self._start()
        other_user, _ = make_provider("+213770200201", self.plomberie, [self.kouba])
        other = APIClient()
        other.force_authenticate(other_user)
        self.assertEqual(other.post(f"/api/provider/payments/{resp.data['payment_id']}/sync/").status_code, 404)

    def test_new_card_page_replaces_unpaid_one(self):
        first, _ = self._start()
        with mock.patch.object(chargily, "retrieve_checkout", return_value={"status": "pending"}):
            second, _ = self._start()
        self.assertEqual(second.status_code, 201)
        self.assertEqual(Payment.objects.get(pk=first.data["payment_id"]).status, "rejected")

    def test_summary_announces_card(self):
        data = self.client.get("/api/provider/points/").data
        self.assertTrue(data["card_enabled"])
        self.assertIsNone(data["pending_card_id"])

    @override_settings(CHARGILY_SECRET_KEY="")
    def test_card_disabled_without_key(self):
        self.assertFalse(self.client.get("/api/provider/points/").data["card_enabled"])
        self.assertEqual(self.client.post("/api/provider/payments/card/").status_code, 400)

    def test_done_page(self):
        page = APIClient().get("/api/billing/paiement-termine/?r=ok")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "BRICOOL Pro")
