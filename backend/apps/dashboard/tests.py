from datetime import timedelta

from django.contrib import admin
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import ProviderProfile, User
from apps.catalog.models import Category
from apps.locations.models import Commune, Wilaya
from apps.marketplace.models import Conversation, Message, Mission, Quote, Review, ServiceRequest

from .site import TTBAdminSite
from .stats import build_dashboard


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        cls.admin = User.objects.create_superuser(phone="+213770000000", password="x")
        cls.client_user = User.objects.create_user(phone="+213661000001", full_name="Sara")
        cls.provider = User.objects.create_user(phone="+213661000002", full_name="Karim", is_provider=True)
        ProviderProfile.objects.create(user=cls.provider, business_name="Karim Plomberie")

        wilaya = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        commune = Commune.objects.create(wilaya=wilaya, name_fr="Kouba")
        category = Category.objects.create(name_fr="Plomberie", order=1)

        def make_request(title, status, published_at):
            return ServiceRequest.objects.create(
                client=cls.client_user, category=category, title=title, description="...",
                wilaya=wilaya, commune=commune, status=status, published_at=published_at,
            )

        # publiée il y a 2 jours, aucun devis → doit apparaître dans « sans devis »
        cls.stale = make_request("Fuite évier", ServiceRequest.Status.PUBLISHED, now - timedelta(days=2))
        # publiée il y a 1 h → trop récente pour être signalée
        make_request("Robinet", ServiceRequest.Status.PUBLISHED, now - timedelta(hours=1))
        make_request("Brouillon", ServiceRequest.Status.DRAFT, None)
        done = make_request("Chauffe-eau", ServiceRequest.Status.COMPLETED, now - timedelta(days=5))

        quote = Quote.objects.create(
            request=done, provider=cls.provider, amount=4000, status=Quote.Status.ACCEPTED,
            valid_until=now + timedelta(days=3),
        )
        mission = Mission.objects.create(
            request=done, quote=quote, provider=cls.provider, status=Mission.Status.PAID, amount_due=4000,
        )
        Review.objects.create(mission=mission, author=cls.client_user, target=cls.provider, rating=4,
                              moderation_status=Review.Moderation.PENDING, comment="Bien")
        conv = Conversation.objects.create(request=done, client=cls.client_user, provider=cls.provider)
        Message.objects.create(conversation=conv, sender=cls.provider, body="appelle-moi au 0550", flagged=True)

    def test_admin_site_is_ttb_site(self):
        self.assertIsInstance(admin.site, TTBAdminSite)
        self.assertIn(User, admin.site._registry)

    def test_figures(self):
        figures = {f["label"]: f["value"] for f in build_dashboard()["ttb_figures"]}
        self.assertEqual(figures["Demandes publiées"], 3)  # le brouillon n'est pas compté
        self.assertEqual(figures["Demandes ouvertes"], 2)
        self.assertEqual(figures["Prestataires"], 1)
        self.assertEqual(figures["Missions terminées"], 1)
        self.assertEqual(figures["Montant des missions terminées"], "4 000 DA")
        self.assertEqual(figures["Note moyenne"], "—")  # le seul avis est en attente

    def test_todo(self):
        todo = {s["title"]: s for s in build_dashboard()["ttb_todo"]}
        self.assertEqual(todo["Prestataires à vérifier"]["count"], 1)
        self.assertEqual(todo["Messages signalés"]["count"], 1)
        self.assertEqual(todo["Avis à modérer"]["count"], 1)
        no_quote = todo["Demandes sans devis depuis plus de 24 h"]
        self.assertEqual(no_quote["count"], 1)
        self.assertIn("Fuite évier", no_quote["items"][0]["text"])

    def test_page_renders_for_staff(self):
        self.client.force_login(self.admin)
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)
        for text in ("À traiter", "Chiffres clés", "Activité récente", "Toutes les tables", "Fuite évier"):
            self.assertContains(resp, text)

    def test_page_requires_staff(self):
        self.client.force_login(self.client_user)
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login/", resp["Location"])
