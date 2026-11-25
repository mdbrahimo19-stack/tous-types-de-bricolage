from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Category, ProviderCategory
from apps.locations.models import Commune, Wilaya

from .tests import make_provider


class ProviderPublicProfileTests(TestCase):
    """Fiche publique d'un prestataire (vue depuis un devis). Plus d'annuaire."""

    @classmethod
    def setUpTestData(cls):
        alger = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        kouba = Commune.objects.create(wilaya=alger, name_fr="Kouba")
        plomberie = Category.objects.create(name_fr="Plomberie", order=1)
        _, cls.p1 = make_provider("+213661000101", plomberie, [kouba])
        cls.p1.base_wilaya = alger
        cls.p1.save()
        ProviderCategory.objects.filter(provider=cls.p1).update(flat_rate=3000, callout_fee=500)

    def setUp(self):
        self.client = APIClient()

    def test_no_public_directory_listing(self):
        self.assertEqual(self.client.get("/api/providers/").status_code, 404)

    def test_profile_exposes_prices_and_wilaya_but_no_phone(self):
        data = self.client.get(f"/api/providers/{self.p1.id}/").data
        self.assertEqual(data["base_wilaya"]["name_fr"], "Alger")
        cat = data["categories"][0]
        self.assertEqual(float(cat["flat_rate"]), 3000)
        self.assertEqual(float(cat["callout_fee"]), 500)
        self.assertNotIn("phone", data)
        self.assertNotIn("+213661000101", str(data))
        self.assertTrue(data["is_verified"])
        self.assertIsInstance(data["member_since"], int)

    def _png(self, name="travail.png"):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (30, 30), (40, 120, 200)).save(buf, format="PNG")
        return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")

    def test_portfolio_upload_public_limit_and_delete(self):
        import shutil
        import tempfile

        from apps.accounts.models import PortfolioPhoto

        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        with self.settings(MEDIA_ROOT=media):
            self.client.force_authenticate(self.p1.user)
            resp = self.client.post(
                "/api/provider/portfolio/", {"image": self._png(), "caption": "Salle de bain"}, format="multipart"
            )
            self.assertEqual(resp.status_code, 201, resp.content)
            photo_id = resp.data["id"]
            self.assertEqual(len(self.client.get("/api/provider/portfolio/").data), 1)

            # visible sur la fiche publique, avec l'adresse complète de l'image
            self.client.force_authenticate(None)
            public = self.client.get(f"/api/providers/{self.p1.id}/").data["portfolio"]
            self.assertEqual(public[0]["caption"], "Salle de bain")
            self.assertTrue(public[0]["image"].startswith("http"))

            # un autre artisan ne peut pas supprimer cette photo
            plomberie = Category.objects.get(name_fr="Plomberie")
            _, other = make_provider("+213661000202", plomberie, [])
            self.client.force_authenticate(other.user)
            self.assertEqual(self.client.delete(f"/api/provider/portfolio/{photo_id}/").status_code, 404)

            # limite de 12 photos
            self.client.force_authenticate(self.p1.user)
            for _ in range(PortfolioPhoto.MAX_PER_PROVIDER - 1):
                PortfolioPhoto.objects.create(provider=self.p1, image="portfolio/x.png")
            full = self.client.post("/api/provider/portfolio/", {"image": self._png()}, format="multipart")
            self.assertEqual(full.status_code, 400)

            # l'artisan supprime sa photo
            self.assertEqual(self.client.delete(f"/api/provider/portfolio/{photo_id}/").status_code, 204)
            self.assertFalse(PortfolioPhoto.objects.filter(pk=photo_id).exists())

    def test_reviews_show_first_name_and_initial_only(self):
        from apps.accounts.models import User

        from .models import Review
        from .serializers import PublicReviewSerializer

        author = User(full_name="Samira Kaci Benali")
        review = Review(author=author, target=self.p1.user, rating=5, comment="Très bien")
        self.assertEqual(PublicReviewSerializer(review).data["author_name"], "Samira K.")
        self.assertEqual(self.client.get(f"/api/providers/{self.p1.id}/reviews/").status_code, 200)
