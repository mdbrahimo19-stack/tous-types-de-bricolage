import io
import json
import urllib.error
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from .models import PhoneOTP
from .sms import SMSError, format_phone, send_sms

HTTP_SETTINGS = dict(
    SMS_BACKEND="http",
    SMS_API_URL="https://sms.example.dz/api/send",
    SMS_API_KEY="secret-key",
    SMS_AUTH_HEADER="Authorization",
    SMS_AUTH_SCHEME="Bearer",
    SMS_SENDER_ID="TTB",
    SMS_PHONE_FORMAT="e164",
    SMS_FIELD_TO="to",
    SMS_FIELD_TEXT="text",
    SMS_FIELD_SENDER="sender",
    SMS_EXTRA_JSON={},
    SMS_TIMEOUT_SECONDS=5,
)


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(code):
    return urllib.error.HTTPError("https://sms.example.dz", code, "err", {}, io.BytesIO(b'{"error": "x"}'))


class FormatPhoneTests(SimpleTestCase):
    def test_formats(self):
        for raw in ("+213555123456", "0555123456", "00213555123456", "213 555 12 34 56"):
            self.assertEqual(format_phone(raw, "e164"), "+213555123456", raw)
            self.assertEqual(format_phone(raw, "intl"), "213555123456", raw)
            self.assertEqual(format_phone(raw, "local"), "0555123456", raw)


@override_settings(**HTTP_SETTINGS)
@mock.patch("apps.accounts.sms.time.sleep")  # pas d'attente réelle entre deux tentatives
class HttpBackendTests(SimpleTestCase):
    @mock.patch("apps.accounts.sms.urllib.request.urlopen", return_value=FakeResponse())
    def test_posts_json_with_key_and_sender(self, urlopen, _sleep):
        self.assertTrue(send_sms("+213555123456", "code 123456"))
        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "https://sms.example.dz/api/send")
        self.assertEqual(req.get_header("Authorization"), "Bearer secret-key")
        self.assertEqual(
            json.loads(req.data), {"to": "+213555123456", "text": "code 123456", "sender": "TTB"}
        )

    @override_settings(
        SMS_FIELD_TO="phone", SMS_FIELD_TEXT="message", SMS_PHONE_FORMAT="local",
        SMS_AUTH_HEADER="X-API-Key", SMS_AUTH_SCHEME="", SMS_SENDER_ID="", SMS_EXTRA_JSON={"type": "otp"},
    )
    @mock.patch("apps.accounts.sms.urllib.request.urlopen", return_value=FakeResponse())
    def test_provider_specific_format(self, urlopen, _sleep):
        send_sms("+213555123456", "hello")
        req = urlopen.call_args.args[0]
        self.assertEqual(req.get_header("X-api-key"), "secret-key")
        self.assertEqual(json.loads(req.data), {"type": "otp", "phone": "0555123456", "message": "hello"})

    @mock.patch("apps.accounts.sms.urllib.request.urlopen", side_effect=[http_error(503), FakeResponse()])
    def test_retries_once_on_server_error(self, urlopen, _sleep):
        self.assertTrue(send_sms("+213555123456", "x"))
        self.assertEqual(urlopen.call_count, 2)

    @mock.patch("apps.accounts.sms.urllib.request.urlopen", side_effect=http_error(401))
    def test_client_error_is_not_retried(self, urlopen, _sleep):
        with self.assertRaises(SMSError):
            send_sms("+213555123456", "x")
        self.assertEqual(urlopen.call_count, 1)

    @mock.patch("apps.accounts.sms.urllib.request.urlopen", side_effect=urllib.error.URLError("down"))
    def test_unreachable_provider_raises_after_retry(self, urlopen, _sleep):
        with self.assertRaises(SMSError):
            send_sms("+213555123456", "x")
        self.assertEqual(urlopen.call_count, 2)

    @override_settings(SMS_API_URL="")
    def test_missing_url_is_a_config_error(self, _sleep):
        with self.assertRaises(SMSError):
            send_sms("+213555123456", "x")


@override_settings(**HTTP_SETTINGS, OTP_EXPOSE_IN_RESPONSE=False)
@mock.patch("apps.accounts.sms.time.sleep")
class OTPRequestWithProviderTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = APIClient()

    def _request(self):
        return self.client.post(
            "/api/auth/otp/request/", {"phone": "+213555123456", "purpose": "registration"}, format="json"
        )

    @mock.patch("apps.accounts.sms.urllib.request.urlopen", return_value=FakeResponse())
    def test_code_sent_by_sms_and_not_exposed(self, urlopen, _sleep):
        resp = self._request()
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("debug_code", resp.data)
        sent_text = json.loads(urlopen.call_args.args[0].data)["text"]
        self.assertRegex(sent_text, r"\b\d{6}\b")
        self.assertEqual(PhoneOTP.objects.count(), 1)

    @mock.patch("apps.accounts.sms.urllib.request.urlopen", side_effect=urllib.error.URLError("down"))
    def test_sms_failure_returns_503_and_drops_code(self, _urlopen, _sleep):
        resp = self._request()
        self.assertEqual(resp.status_code, 503)
        self.assertIn("SMS", resp.data["detail"])
        self.assertEqual(PhoneOTP.objects.count(), 0)
