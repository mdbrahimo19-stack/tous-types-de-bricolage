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
