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
            {"phone": PHONE, "code": code, "purpose": "registration", "full_name": "Amine", "as_provider": True,
             "accept_privacy": True},
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

    def test_registration_in_english(self):
        code = self._request_code()
        resp = self.client.post(
            "/api/auth/otp/verify/",
            {"phone": PHONE, "code": code, "purpose": "registration", "full_name": "Sam",
             "language": "en", "accept_privacy": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["user"]["language"], "en")

    def test_wrong_code_is_rejected_and_counts_attempts(self):
        self._request_code()
        resp = self.client.post(
            "/api/auth/otp/verify/",
            {"phone": PHONE, "code": "000000", "purpose": "registration", "accept_privacy": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(PhoneOTP.objects.latest("created_at").attempts, 1)
        self.assertFalse(User.objects.filter(phone=PHONE).exists())

    def test_code_is_single_use(self):
        code = self._request_code()
        first = self.client.post(
            "/api/auth/otp/verify/", {"phone": PHONE, "code": code, "purpose": "registration", "accept_privacy": True}, format="json"
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            "/api/auth/otp/verify/", {"phone": PHONE, "code": code, "purpose": "registration", "accept_privacy": True}, format="json"
        )
        self.assertEqual(second.status_code, 400)

    def test_registration_without_privacy_consent_is_refused_and_code_kept(self):
        code = self._request_code()
        resp = self.client.post(
            "/api/auth/otp/verify/", {"phone": PHONE, "code": code, "purpose": "registration"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "privacy_required")
        self.assertFalse(User.objects.filter(phone=PHONE).exists())
        # le code n'a pas été consommé : l'utilisateur coche la case et réessaie
        ok = self.client.post(
            "/api/auth/otp/verify/",
            {"phone": PHONE, "code": code, "purpose": "registration", "accept_privacy": True},
            format="json",
        )
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertFalse(ok.data["user"]["privacy_required"])
        user = User.objects.get(phone=PHONE)
        self.assertTrue(user.privacy_version)
        self.assertIsNotNone(user.privacy_accepted_at)

    def test_existing_user_accepts_new_policy(self):
        user = User.objects.create_user(phone=PHONE, full_name="Sara", phone_verified=True)
        self.client.force_authenticate(user)
        self.assertTrue(self.client.get("/api/auth/me/").data["privacy_required"])
        resp = self.client.post("/api/auth/me/privacy/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["privacy_required"])

    def test_landing_site_fr_and_ar(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Trouvez le bon artisan")
        self.assertContains(page, "bricool.apk")
        self.assertNotContains(page, "bricool-pro.apk")  # une seule application
        self.assertContains(page, "Une application, deux espaces")
        ar = self.client.get("/?lang=ar")
        self.assertContains(ar, 'dir="rtl"')
        self.assertContains(ar, "اعثر على الحرفي المناسب")

    def test_landing_site_in_english(self):
        from .models import SiteText

        en = self.client.get("/?lang=en")
        self.assertEqual(en.status_code, 200)
        self.assertContains(en, 'lang="en"')
        self.assertContains(en, 'dir="ltr"')
        self.assertContains(en, "Find the right professional")
        self.assertContains(en, "One app, two spaces")
        self.assertContains(en, "Plumbing")
        self.assertContains(en, "/confidentialite/#en")
        # liens vers les deux autres langues
        self.assertContains(en, "?lang=fr")
        self.assertContains(en, "?lang=ar")
        # texte anglais modifiable dans l'administration
        SiteText.objects.create(key="h1", fr="", ar="", en="Your pro in 1 click")
        self.assertContains(self.client.get("/?lang=en"), "Your pro in 1 click")
        self.assertNotContains(self.client.get("/"), "Your pro in 1 click")

    def test_landing_texts_editable_in_admin(self):
        from .models import SiteText

        SiteText.objects.create(key="announcement", fr="Promo : 100 points offerts !", ar="")
        SiteText.objects.create(key="h1", fr="Votre artisan en 1 clic", ar="")
        page = self.client.get("/")
        self.assertContains(page, "Promo : 100 points offerts !")
        self.assertContains(page, "Votre artisan en 1 clic")
        self.assertNotContains(self.client.get("/?lang=ar"), "Promo : 100 points")  # arabe vide = défaut

    def test_privacy_policy_page_is_public(self):
        page = self.client.get("/confidentialite/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "18-07")
        self.assertContains(page, "سياسة الخصوصية")
        # version anglaise (troisième langue de l'app)
        self.assertContains(page, 'id="en"')
        self.assertContains(page, "Privacy policy")
        self.assertContains(page, "Law No. 18-07")

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

    def test_login_from_pro_app_makes_client_a_pending_provider(self):
        User.objects.create_user(phone=PHONE, full_name="Sara", phone_verified=True)
        code = self._request_code(purpose="login")
        resp = self.client.post(
            "/api/auth/otp/verify/",
            {"phone": PHONE, "code": code, "purpose": "login", "as_provider": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.data["user"]["is_provider"])
        self.assertEqual(resp.data["user"]["provider_profile"]["verification_status"], "pending")
        user = User.objects.get(phone=PHONE)
        self.assertTrue(ProviderProfile.objects.filter(user=user).exists())

    def test_login_from_client_app_keeps_roles(self):
        User.objects.create_user(phone=PHONE, full_name="Sara", phone_verified=True)
        code = self._request_code(purpose="login")
        resp = self.client.post(
            "/api/auth/otp/verify/",
            {"phone": PHONE, "code": code, "purpose": "login", "as_provider": False},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(resp.data["user"]["is_provider"])

    def test_photo_upload_and_delete(self):
        import io
        import shutil
        import tempfile

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        buf = io.BytesIO()
        Image.new("RGB", (40, 40), (200, 90, 10)).save(buf, format="PNG")
        user = User.objects.create_user(phone=PHONE, full_name="Ahmed", phone_verified=True)
        self.client.force_authenticate(user)

        with self.settings(MEDIA_ROOT=media):
            self.assertEqual(self.client.post("/api/auth/me/photo/", {}, format="multipart").status_code, 400)
            photo = SimpleUploadedFile("moi.png", buf.getvalue(), content_type="image/png")
            resp = self.client.post("/api/auth/me/photo/", {"photo": photo}, format="multipart")
            self.assertEqual(resp.status_code, 200, resp.content)
            self.assertTrue(resp.data["photo"].startswith("http"))
            user.refresh_from_db()
            self.assertTrue(user.photo)

            resp = self.client.delete("/api/auth/me/photo/")
            self.assertEqual(resp.status_code, 200)
            self.assertIsNone(resp.data["photo"])

    def test_photo_rejects_non_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        user = User.objects.create_user(phone=PHONE, full_name="Ahmed", phone_verified=True)
        self.client.force_authenticate(user)
        fake = SimpleUploadedFile("virus.png", b"pas une image", content_type="image/png")
        resp = self.client.post("/api/auth/me/photo/", {"photo": fake}, format="multipart")
        self.assertEqual(resp.status_code, 400)

    def test_me_endpoint_requires_auth_and_returns_profile(self):
        code = self._request_code()
        tokens = self.client.post(
            "/api/auth/otp/verify/", {"phone": PHONE, "code": code, "purpose": "registration", "accept_privacy": True}, format="json"
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
