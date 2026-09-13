from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import ClientProfile, PhoneOTP, ProviderProfile, User

PHONE = "+213661234567"


@override_settings(SMS_BACKEND="console", OTP_EXPOSE_IN_RESPONSE=True)
class OTPAuthFlowTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()  # les compteurs de throttle vivent dans le cache, pas la DB
        self.client = APIClient()

    def _request_code(self, phone=PHONE, purpose="registration"):
        resp = self.client.post(
            "/api/auth/otp/request/", {"phone": phone, "purpose": purpose}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.data["debug_code"]

    def test_registration_creates_verified_user_and_profiles(self):
        code = self._request_code()
        resp = self.client.post(
            "/api/auth/otp/verify/",
            {"phone": PHONE, "code": code, "purpose": "registration", "full_name": "Amine", "as_provider": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.data["created"])
        self.assertIn("access", resp.data["tokens"])

        user = User.objects.get(phone=PHONE)
        self.assertTrue(user.phone_verified)
        self.assertTrue(user.is_provider)
        self.assertTrue(ClientProfile.objects.filter(user=user).exists())
        self.assertTrue(ProviderProfile.objects.filter(user=user).exists())

    def test_wrong_code_is_rejected_and_counts_attempts(self):
        self._request_code()
        resp = self.client.post(
            "/api/auth/otp/verify/",
            {"phone": PHONE, "code": "000000", "purpose": "registration"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(PhoneOTP.objects.latest("created_at").attempts, 1)
        self.assertFalse(User.objects.filter(phone=PHONE).exists())

    def test_code_is_single_use(self):
        code = self._request_code()
        first = self.client.post(
            "/api/auth/otp/verify/", {"phone": PHONE, "code": code, "purpose": "registration"}, format="json"
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            "/api/auth/otp/verify/", {"phone": PHONE, "code": code, "purpose": "registration"}, format="json"
        )
        self.assertEqual(second.status_code, 400)

    def test_login_requires_existing_account(self):
        resp = self.client.post(
            "/api/auth/otp/request/", {"phone": PHONE, "purpose": "login"}, format="json"
        )
        self.assertEqual(resp.status_code, 404)

    def test_login_returns_tokens_for_existing_user(self):
        User.objects.create_user(phone=PHONE, full_name="Sara", phone_verified=True)
        code = self._request_code(purpose="login")
        resp = self.client.post(
            "/api/auth/otp/verify/", {"phone": PHONE, "code": code, "purpose": "login"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(resp.data["created"])

    def test_me_endpoint_requires_auth_and_returns_profile(self):
        code = self._request_code()
        tokens = self.client.post(
            "/api/auth/otp/verify/", {"phone": PHONE, "code": code, "purpose": "registration"}, format="json"
        ).data["tokens"]

        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = self.client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["phone"], PHONE)


class UserModelTests(TestCase):
    def test_create_superuser(self):
        admin = User.objects.create_superuser(phone="+213770000000", password="x")
        self.assertTrue(admin.is_staff and admin.is_superuser and admin.phone_verified)

    def test_phone_is_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(phone="", password="x")
