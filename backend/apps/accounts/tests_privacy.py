"""Droits des personnes (loi 18-07) : export, suppression (anonymisation) et nettoyage automatique."""
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.billing import services as billing
from apps.catalog.models import Category
from apps.locations.models import Commune, Wilaya
from apps.marketplace.models import Notification
from apps.marketplace.tests import make_provider, make_user

from . import privacy
from .models import PhoneOTP, User


class PrivacyRightsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        alger = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        cls.kouba = Commune.objects.create(wilaya=alger, name_fr="Kouba")
        cls.plomberie = Category.objects.create(name_fr="Plomberie", order=1)

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_export_contains_my_data_and_requires_login(self):
        self.assertEqual(self.client.get("/api/auth/me/export/").status_code, 401)
        user, profile = make_provider("+213661000901", self.plomberie, [self.kouba])
        self.client.force_authenticate(user)
        data = self.client.get("/api/auth/me/export/").data
        self.assertEqual(data["compte"]["telephone"], "+213661000901")
        self.assertIn("profil_artisan", data)
        self.assertIn("demandes", data)
        self.assertNotIn("password", str(data))
        self.assertNotIn("verification_notes", data["profil_artisan"])

    def test_delete_anonymizes_and_closes_account(self):
        user = make_user("+213661000902")
        Notification.objects.create(recipient=user, type="x", title="t", body="b")
        self.client.force_authenticate(user)
        self.assertEqual(self.client.post("/api/auth/me/delete/", {}, format="json").status_code, 400)
        resp = self.client.post("/api/auth/me/delete/", {"confirm": True}, format="json")
        self.assertEqual(resp.status_code, 204)
        user.refresh_from_db()
        self.assertEqual(user.full_name, privacy.DELETED_NAME)
        self.assertFalse(user.is_active)
        self.assertNotEqual(str(user.phone), "+213661000902")
        self.assertFalse(Notification.objects.filter(recipient=user).exists())
        # le vrai numéro est libéré : on peut s'inscrire de nouveau avec
        self.assertFalse(User.objects.filter(phone="+213661000902").exists())

    def test_provider_with_points_due_cannot_delete(self):
        user, profile = make_provider("+213661000903", self.plomberie, [self.kouba])
        account = billing.account_for(profile)
        account.points_due = 25
        account.save()
        self.client.force_authenticate(user)
        resp = self.client.post("/api/auth/me/delete/", {"confirm": True}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "deletion_blocked")
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_purge_old_codes_and_inactive_accounts(self):
        old = timezone.now() - timedelta(days=2)
        otp = PhoneOTP.objects.create(phone="+213661000904", code_hash="x", purpose="login", expires_at=old)
        PhoneOTP.objects.filter(pk=otp.pk).update(created_at=old)
        sleeper = make_user("+213661000905")
        User.objects.filter(pk=sleeper.pk).update(last_seen_at=timezone.now() - timedelta(days=365 * 4))
        recent = make_user("+213661000906")

        dry = privacy.purge(dry_run=True)
        self.assertEqual((dry["codes_sms"], dry["comptes_inactifs"]), (1, 1))
        self.assertTrue(PhoneOTP.objects.filter(pk=otp.pk).exists())  # rien effacé en essai

        privacy.purge()
        self.assertFalse(PhoneOTP.objects.filter(pk=otp.pk).exists())
        sleeper.refresh_from_db()
        recent.refresh_from_db()
        self.assertFalse(sleeper.is_active)
        self.assertTrue(recent.is_active)
