"""Notifications push (Firebase Cloud Messaging) : sonnerie, langue de l'artisan, jetons périmés."""
from unittest import mock

from django.test import TestCase, override_settings

from apps.catalog.models import Category
from apps.locations.models import Commune, Wilaya

from . import push_fcm
from .dispatch import _nearby_text
from .models import ServiceRequest
from .notifications import notify
from .tests import make_user


class _FakeResponse:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload


class _FakeSession:
    """Remplace Google : enregistre les messages et répond « jeton inconnu » pour les jetons « dead- »."""

    def __init__(self):
        self.sent = []

    def post(self, url, json=None, timeout=None):
        self.sent.append((url, json))
        if json["message"]["token"].startswith("dead-"):
            return _FakeResponse(404, {"error": {"status": "NOT_FOUND",
                                                 "details": [{"errorCode": "UNREGISTERED"}]}})
        return _FakeResponse(200, {"name": "projects/x/messages/1"})


@override_settings(PUSH_BACKEND="fcm")
class FcmPushTests(TestCase):
    def setUp(self):
        self.user = make_user(phone="+213661000900")
        self.user.devices.create(token="good-token-123")
        self.user.devices.create(token="dead-token-456")
        self.session = _FakeSession()
        patcher = mock.patch.object(push_fcm, "_client", return_value=(self.session, "bricool-test"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_push_rings_and_forgets_uninstalled_phones(self):
        notify(self.user, "request_nearby", "Nouvelle demande près de vous", "Plomberie à 2 km",
               data={"request_id": 7})
        self.assertEqual(len(self.session.sent), 2)
        url, body = self.session.sent[0]
        self.assertIn("/projects/bricool-test/messages:send", url)
        msg = body["message"]
        self.assertEqual(msg["notification"]["title"], "Nouvelle demande près de vous")
        self.assertEqual(msg["android"]["priority"], "high")
        self.assertEqual(msg["android"]["notification"]["sound"], "default")
        self.assertEqual(msg["android"]["notification"]["channel_id"], push_fcm.ANDROID_CHANNEL)
        self.assertEqual(msg["data"], {"request_id": "7"})  # FCM n'accepte que du texte
        # l'app désinstallée est oubliée, l'autre téléphone est gardé
        self.assertEqual(list(self.user.devices.values_list("token", flat=True)), ["good-token-123"])

    def test_push_failure_never_breaks_the_notification(self):
        with mock.patch.object(push_fcm, "send", side_effect=RuntimeError("Google injoignable")):
            notif = notify(self.user, "message", "Nouveau message")
        self.assertIsNotNone(notif.pk)  # la notification est quand même enregistrée


class NearbyTextTests(TestCase):
    def test_text_in_the_professional_language(self):
        wilaya = Wilaya.objects.create(code="16", name_fr="Alger", name_ar="الجزائر", is_active=True)
        commune = Commune.objects.create(wilaya=wilaya, name_fr="Kouba", name_ar="القبة")
        category = Category.objects.create(name_fr="Plomberie", name_ar="سباكة", order=1)
        req = ServiceRequest(title="Fuite", category=category, wilaya=wilaya, commune=commune)

        self.assertEqual(_nearby_text(req, 2.5, "fr"),
                         ("Nouvelle demande près de vous", "Plomberie à 2,5 km : « Fuite »."))
        self.assertEqual(_nearby_text(req, 2.5, "en"),
                         ("New request near you", "Plumbing 2.5 km away: “Fuite”."))
        title, body = _nearby_text(req, None, "ar")
        self.assertEqual(title, "طلب جديد بالقرب منك")
        self.assertIn("سباكة", body)
        self.assertIn("القبة", body)
