from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Category, ProviderCategory
from apps.locations.models import Commune, Wilaya

from .tests import make_provider


class ProviderDirectoryTests(TestCase):
    """GET /api/providers/ : annuaire public des prestataires validés."""

    @classmethod
    def setUpTestData(cls):
        alger = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        oran = Wilaya.objects.create(code="31", name_fr="Oran", is_active=True)
        cls.kouba = Commune.objects.create(wilaya=alger, name_fr="Kouba")
        cls.bir_el_djir = Commune.objects.create(wilaya=oran, name_fr="Bir El Djir")
        cls.alger, cls.oran = alger, oran

        cls.plomberie = Category.objects.create(name_fr="Plomberie", order=1)
        cls.fuite = Category.objects.create(name_fr="Recherche de fuite", parent=cls.plomberie, order=1)
        cls.peinture = Category.objects.create(name_fr="Peinture", order=2)

        # plombier à Alger, bien noté, avec un forfait
        _, cls.p1 = make_provider("+213661000101", cls.plomberie, [cls.kouba])
        cls.p1.user.full_name = "Karim Plombier"
        cls.p1.user.save()
        cls.p1.base_wilaya = alger
        cls.p1.rating_avg, cls.p1.reviews_count, cls.p1.missions_count = 4.8, 12, 30
        cls.p1.save()
        ProviderCategory.objects.filter(provider=cls.p1).update(flat_rate=3000, callout_fee=500)

        # spécialiste « recherche de fuite » (sous-catégorie) à Oran, indisponible
        _, cls.p2 = make_provider("+213661000102", cls.fuite, [cls.bir_el_djir])
        cls.p2.is_available = False
        cls.p2.rating_avg = 4.0
        cls.p2.save()

        # peintre à Alger
        _, cls.p3 = make_provider("+213661000103", cls.peinture, [cls.kouba])

        # plombier non validé : ne doit jamais apparaître
        make_provider("+213661000104", cls.plomberie, [cls.kouba], verified=False)

    def setUp(self):
        self.client = APIClient()  # anonyme : l'annuaire est public

    def ids(self, **params):
        resp = self.client.get("/api/providers/", params)
        self.assertEqual(resp.status_code, 200, resp.data)
        return [p["id"] for p in resp.data["results"]]

    def test_lists_only_approved_providers(self):
        self.assertCountEqual(self.ids(), [self.p1.id, self.p2.id, self.p3.id])

    def test_filter_by_family_includes_subcategories(self):
        self.assertCountEqual(self.ids(category=self.plomberie.id), [self.p1.id, self.p2.id])
        self.assertEqual(self.ids(category=self.fuite.id), [self.p2.id])

    def test_filter_by_wilaya_and_commune(self):
        self.assertCountEqual(self.ids(wilaya=self.alger.id), [self.p1.id, self.p3.id])
        self.assertEqual(self.ids(commune=self.bir_el_djir.id), [self.p2.id])
        self.assertEqual(self.ids(category=self.plomberie.id, wilaya=self.oran.id), [self.p2.id])

    def test_filter_available_and_search(self):
        self.assertNotIn(self.p2.id, self.ids(available=1))
        self.assertEqual(self.ids(search="karim"), [self.p1.id])

    def test_default_order_available_then_rating(self):
        ids = self.ids()
        self.assertEqual(ids[0], self.p1.id)  # disponible et le mieux noté
        self.assertEqual(ids[-1], self.p2.id)  # indisponible en dernier

    def test_profile_exposes_prices_and_wilaya_but_no_phone(self):
        data = self.client.get(f"/api/providers/{self.p1.id}/").data
        self.assertEqual(data["base_wilaya"]["name_fr"], "Alger")
        cat = data["categories"][0]
        self.assertEqual(float(cat["flat_rate"]), 3000)
        self.assertEqual(float(cat["callout_fee"]), 500)
        self.assertNotIn("phone", data)
        self.assertNotIn("+213661000101", str(data))

    def test_invalid_filter_is_rejected(self):
        self.assertEqual(self.client.get("/api/providers/", {"wilaya": "abc"}).status_code, 400)
