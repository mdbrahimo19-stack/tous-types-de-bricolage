from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import ClientProfile, ProviderProfile, User
from apps.catalog.models import Category, ProviderCategory
from apps.locations.models import Commune, Wilaya
from apps.marketplace.models import Mission, Quote, ServiceRequest


def make_provider(phone, category, communes, *, verified=True, lat=None, lng=None):
    user = User.objects.create_user(
        phone=phone, phone_verified=True, is_provider=True, full_name="Presta Test"
    )
    ClientProfile.objects.create(user=user)
    profile = ProviderProfile.objects.create(
        user=user,
        verification_status=(
            ProviderProfile.Verification.APPROVED if verified else ProviderProfile.Verification.PENDING
        ),
        latitude=lat,
        longitude=lng,
    )
    profile.service_communes.set(communes)
    ProviderCategory.objects.create(provider=profile, category=category)
    return user, profile


def make_user(phone="+213661000001", **kw):
    user = User.objects.create_user(phone=phone, phone_verified=True, full_name="Client Test", **kw)
    ClientProfile.objects.create(user=user)
    return user


@override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}})
class ServiceRequestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.wilaya = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        cls.commune = Commune.objects.create(wilaya=cls.wilaya, name_fr="Kouba")
        cls.other_commune = Commune.objects.create(
            wilaya=Wilaya.objects.create(code="31", name_fr="Oran"), name_fr="Bir El Djir"
        )
        cls.category = Category.objects.create(name_fr="Plomberie", unit="forfait", order=1)

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _payload(self, **over):
        data = {
            "category": self.category.id,
            "title": "Fuite sous l'évier",
            "description": "Goutte à goutte depuis hier soir, eau non coupée.",
            "wilaya": self.wilaya.id,
            "commune": self.commune.id,
            "urgency": "today",
        }
        data.update(over)
        return data

    def test_create_draft_then_publish_sets_dates(self):
        resp = self.client.post("/api/requests/", self._payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["status"], "draft")
        self.assertEqual(resp.data["wilaya"], self.wilaya.id)

        rid = resp.data["id"]
        pub = self.client.post(f"/api/requests/{rid}/publish/")
        self.assertEqual(pub.status_code, 200, pub.content)
        self.assertEqual(pub.data["status"], "published")
        self.assertIsNotNone(pub.data["published_at"])
        self.assertIsNotNone(pub.data["expires_at"])

    def test_publish_now_shortcut(self):
        resp = self.client.post("/api/requests/", self._payload(publish_now=True), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(ServiceRequest.objects.get(pk=resp.data["id"]).status, "published")

    def test_commune_must_belong_to_wilaya(self):
        resp = self.client.post(
            "/api/requests/", self._payload(commune=self.other_commune.id), format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_max_active_requests_rule(self):
        for i in range(5):
            r = self.client.post("/api/requests/", self._payload(title=f"D{i}", publish_now=True), format="json")
            self.assertEqual(r.status_code, 201, r.content)
        blocked = self.client.post("/api/requests/", self._payload(title="6e"), format="json")
        rid = blocked.data["id"]
        resp = self.client.post(f"/api/requests/{rid}/publish/")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("RG-03", str(resp.data))

    def test_only_draft_is_editable(self):
        r = self.client.post("/api/requests/", self._payload(publish_now=True), format="json")
        rid = r.data["id"]
        resp = self.client.patch(f"/api/requests/{rid}/", {"title": "Nouveau titre"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_cancel_active_request(self):
        r = self.client.post("/api/requests/", self._payload(publish_now=True), format="json")
        resp = self.client.post(f"/api/requests/{r.data['id']}/cancel/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "cancelled")

    def test_user_sees_only_own_requests(self):
        self.client.post("/api/requests/", self._payload(), format="json")
        other = make_user(phone="+213661000002")
        c2 = APIClient()
        c2.force_authenticate(other)
        self.assertEqual(c2.get("/api/requests/").data["count"], 0)
        self.assertEqual(self.client.get("/api/requests/").data["count"], 1)

    def test_anonymous_cannot_create(self):
        self.assertEqual(APIClient().post("/api/requests/", self._payload(), format="json").status_code, 401)


@override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}})
class CatalogAndAddressTests(TestCase):
    def setUp(self):
        self.wilaya = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        self.commune = Commune.objects.create(wilaya=self.wilaya, name_fr="El Biar")
        root = Category.objects.create(name_fr="Électricité", order=1)
        Category.objects.create(name_fr="Tableau électrique", parent=root, order=1)
        self.user = make_user()
        self.client = APIClient()

    def test_categories_public_and_nested(self):
        resp = self.client.get("/api/categories/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)  # racine seulement
        self.assertEqual(len(resp.data["results"][0]["children"]), 1)

    def test_address_crud_scoped_to_user(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post(
            "/api/addresses/",
            {"label": "domicile", "wilaya": self.wilaya.id, "commune": self.commune.id, "is_default": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        other = make_user(phone="+213661000003")
        c2 = APIClient()
        c2.force_authenticate(other)
        self.assertEqual(c2.get("/api/addresses/").data["count"], 0)


@override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}})
class FeedQuoteMissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.wilaya = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        cls.kouba = Commune.objects.create(wilaya=cls.wilaya, name_fr="Kouba")
        cls.rouiba = Commune.objects.create(wilaya=cls.wilaya, name_fr="Rouiba")
        cls.plomberie = Category.objects.create(name_fr="Plomberie", order=1)
        cls.peinture = Category.objects.create(name_fr="Peinture", order=2)

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client_user = make_user(phone="+213661111111")
        self.cc = APIClient()
        self.cc.force_authenticate(self.client_user)

    def _publish_request(self, category=None, commune=None, lat="36.72", lng="3.09", urgency="today"):
        r = ServiceRequest.objects.create(
            client=self.client_user,
            category=category or self.plomberie,
            title="Fuite",
            description="desc",
            wilaya=self.wilaya,
            commune=commune or self.kouba,
            latitude=lat,
            longitude=lng,
            urgency=urgency,
        )
        r.publish()
        return r

    def test_feed_matches_category_and_commune_only(self):
        self._publish_request(category=self.plomberie, commune=self.kouba)
        self._publish_request(category=self.peinture, commune=self.kouba)   # mauvaise catégorie
        self._publish_request(category=self.plomberie, commune=self.rouiba)  # mauvaise commune

        prov_user, _ = make_provider("+213770000001", self.plomberie, [self.kouba], lat="36.73", lng="3.10")
        pc = APIClient()
        pc.force_authenticate(prov_user)
        resp = pc.get("/api/feed/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["count"], 1)
        self.assertIsNotNone(resp.data["results"][0]["distance_km"])
        self.assertFalse(resp.data["results"][0]["already_quoted"])

    def test_unverified_provider_blocked_from_feed(self):
        prov_user, _ = make_provider("+213770000002", self.plomberie, [self.kouba], verified=False)
        pc = APIClient()
        pc.force_authenticate(prov_user)
        self.assertEqual(pc.get("/api/feed/").status_code, 403)

    def test_quote_flow_and_acceptance_creates_mission(self):
        req = self._publish_request()
        p1_user, _ = make_provider("+213770000003", self.plomberie, [self.kouba])
        p2_user, _ = make_provider("+213770000004", self.plomberie, [self.kouba])
        pc1, pc2 = APIClient(), APIClient()
        pc1.force_authenticate(p1_user)
        pc2.force_authenticate(p2_user)

        q1 = pc1.post("/api/quotes/", {"request": req.id, "amount": "3500", "lead_time_days": 1,
                                       "message": "Dispo demain"}, format="json")
        self.assertEqual(q1.status_code, 201, q1.content)
        req.refresh_from_db()
        self.assertEqual(req.status, "quotes_received")

        q2 = pc2.post("/api/quotes/", {"request": req.id, "amount": "4200", "lead_time_days": 2},
                      format="json")
        self.assertEqual(q2.status_code, 201, q2.content)

        # doublon interdit
        dup = pc1.post("/api/quotes/", {"request": req.id, "amount": "3000", "lead_time_days": 1},
                       format="json")
        self.assertEqual(dup.status_code, 400)

        # le client compare
        listing = self.cc.get(f"/api/requests/{req.id}/quotes/")
        self.assertEqual(len(listing.data), 2)

        # un autre prestataire ne peut pas accepter (devis hors de son périmètre -> 404)
        self.assertIn(pc2.post(f"/api/quotes/{q1.data['id']}/accept/").status_code, (403, 404))

        # le client accepte le devis 1
        acc = self.cc.post(f"/api/quotes/{q1.data['id']}/accept/")
        self.assertEqual(acc.status_code, 201, acc.content)
        self.assertEqual(acc.data["client_contact"]["phone"], "+213661111111")
        self.assertEqual(acc.data["provider_contact"]["phone"], "+213770000003")

        req.refresh_from_db()
        self.assertEqual(req.status, "assigned")
        self.assertEqual(Quote.objects.get(pk=q2.data["id"]).status, "rejected")
        self.assertEqual(Mission.objects.count(), 1)

    def test_quote_rejected_when_out_of_zone(self):
        req = self._publish_request(commune=self.rouiba)
        prov_user, _ = make_provider("+213770000005", self.plomberie, [self.kouba])
        pc = APIClient()
        pc.force_authenticate(prov_user)
        resp = pc.post("/api/quotes/", {"request": req.id, "amount": "3000", "lead_time_days": 1},
                       format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("zone", str(resp.data))

    def test_provider_category_limit(self):
        prov_user, _ = make_provider("+213770000006", self.plomberie, [self.kouba])
        pc = APIClient()
        pc.force_authenticate(prov_user)
        cats = [Category.objects.create(name_fr=f"Cat{i}", order=10 + i) for i in range(5)]
        for c in cats[:4]:
            self.assertEqual(
                pc.post("/api/provider/categories/", {"category": c.id}, format="json").status_code, 201
            )
        # 1 (initiale) + 4 = 5 -> la 6e est refusée
        self.assertEqual(
            pc.post("/api/provider/categories/", {"category": cats[4].id}, format="json").status_code, 400
        )


@override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}})
class MessagingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.wilaya = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        cls.kouba = Commune.objects.create(wilaya=cls.wilaya, name_fr="Kouba")
        cls.plomberie = Category.objects.create(name_fr="Plomberie", order=1)

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client_user = make_user(phone="+213661222333")
        self.prov_user, _ = make_provider("+213770333444", self.plomberie, [self.kouba])
        self.cc = APIClient(); self.cc.force_authenticate(self.client_user)
        self.pc = APIClient(); self.pc.force_authenticate(self.prov_user)

        self.req = ServiceRequest.objects.create(
            client=self.client_user, category=self.plomberie, title="Fuite",
            description="d", wilaya=self.wilaya, commune=self.kouba, urgency="today",
        )
        self.req.publish()
        self.quote = self.pc.post(
            "/api/quotes/", {"request": self.req.id, "amount": "3000", "lead_time_days": 1}, format="json"
        )
        self.assertEqual(self.quote.status_code, 201, self.quote.content)

    def _conv_id(self):
        return self.cc.get("/api/conversations/").data["results"][0]["id"]

    def test_conversation_created_on_quote_and_notification_sent(self):
        convs = self.cc.get("/api/conversations/")
        self.assertEqual(convs.data["count"], 1)
        self.assertEqual(self.cc.get("/api/notifications/unread_count/").data["unread"], 1)

    def test_phone_number_masked_before_attribution(self):
        cid = self._conv_id()
        resp = self.pc.post(
            f"/api/conversations/{cid}/messages/",
            {"type": "text", "body": "Appelle moi au 0770 33 44 55 stp"}, format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertNotIn("0770", resp.data["body"])
        self.assertTrue(resp.data["was_filtered"])

    def test_contacts_visible_after_attribution(self):
        self.cc.post(f"/api/quotes/{self.quote.data['id']}/accept/")
        cid = self._conv_id()
        resp = self.pc.post(
            f"/api/conversations/{cid}/messages/",
            {"type": "text", "body": "Mon numero direct 0770334455"}, format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn("0770334455", resp.data["body"])
        self.assertFalse(resp.data["was_filtered"])

    def test_losing_provider_conversation_is_locked(self):
        p2, _ = make_provider("+213770999888", self.plomberie, [self.kouba])
        pc2 = APIClient(); pc2.force_authenticate(p2)
        q2 = pc2.post("/api/quotes/", {"request": self.req.id, "amount": "5000", "lead_time_days": 3}, format="json")
        self.cc.post(f"/api/quotes/{self.quote.data['id']}/accept/")  # accepte le 1er presta

        cid2 = pc2.get("/api/conversations/").data["results"][0]["id"]
        resp = pc2.post(f"/api/conversations/{cid2}/messages/", {"type": "text", "body": "encore dispo?"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_outsider_cannot_read_conversation(self):
        cid = self._conv_id()
        outsider = make_user(phone="+213661000999")
        oc = APIClient(); oc.force_authenticate(outsider)
        self.assertEqual(oc.get(f"/api/conversations/{cid}/messages/").status_code, 404)

    def test_read_marks_messages(self):
        cid = self._conv_id()
        self.pc.post(f"/api/conversations/{cid}/messages/", {"type": "text", "body": "bonjour"}, format="json")
        # client a 1 non-lu
        conv = next(c for c in self.cc.get("/api/conversations/").data["results"] if c["id"] == cid)
        self.assertEqual(conv["unread_count"], 1)
        self.cc.get(f"/api/conversations/{cid}/messages/")  # lecture -> marque lu
        conv = next(c for c in self.cc.get("/api/conversations/").data["results"] if c["id"] == cid)
        self.assertEqual(conv["unread_count"], 0)


@override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}})
class MissionLifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.wilaya = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        cls.kouba = Commune.objects.create(wilaya=cls.wilaya, name_fr="Kouba")
        cls.plomberie = Category.objects.create(name_fr="Plomberie", order=1)

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client_user = make_user(phone="+213661555666")
        self.prov_user, self.profile = make_provider("+213770555666", self.plomberie, [self.kouba])
        self.cc = APIClient(); self.cc.force_authenticate(self.client_user)
        self.pc = APIClient(); self.pc.force_authenticate(self.prov_user)

        req = ServiceRequest.objects.create(
            client=self.client_user, category=self.plomberie, title="Fuite",
            description="d", wilaya=self.wilaya, commune=self.kouba, urgency="today",
        )
        req.publish()
        q = self.pc.post("/api/quotes/", {"request": req.id, "amount": "4000", "lead_time_days": 1}, format="json")
        self.mission_id = self.cc.post(f"/api/quotes/{q.data['id']}/accept/").data["id"]

    def _full_run_until_completed(self):
        from django.utils import timezone as tz
        from datetime import timedelta

        when = (tz.now() + timedelta(days=1)).isoformat()
        self.pc.post(f"/api/missions/{self.mission_id}/schedule/", {"scheduled_at": when}, format="json")
        self.cc.post(f"/api/missions/{self.mission_id}/confirm/")
        r = self.pc.post(f"/api/missions/{self.mission_id}/confirm/")
        self.assertEqual(r.data["status"], "confirmed")
        self.pc.post(f"/api/missions/{self.mission_id}/start/")
        return self.pc.post(f"/api/missions/{self.mission_id}/complete/")

    def test_happy_path_schedule_start_complete_pay_review(self):
        r = self._full_run_until_completed()
        self.assertEqual(r.data["status"], "completed")

        # paiement : les deux confirment
        self.cc.post(f"/api/missions/{self.mission_id}/pay/")
        r = self.pc.post(f"/api/missions/{self.mission_id}/confirm-payment/")
        self.assertEqual(r.data["status"], "paid")

        # avis
        rv = self.cc.post(f"/api/missions/{self.mission_id}/review/",
                          {"rating": 5, "comment": "Rapide et propre"}, format="json")
        self.assertEqual(rv.status_code, 201, rv.content)
        self.profile.refresh_from_db()
        self.assertEqual(float(self.profile.rating_avg), 5.0)
        self.assertEqual(self.profile.reviews_count, 1)
        self.assertEqual(self.profile.missions_count, 1)

        req = ServiceRequest.objects.get(mission__id=self.mission_id)
        self.assertEqual(req.status, "evaluated")

    def test_provider_only_can_start(self):
        from django.utils import timezone as tz
        from datetime import timedelta

        self.pc.post(f"/api/missions/{self.mission_id}/schedule/",
                     {"scheduled_at": (tz.now() + timedelta(days=1)).isoformat()}, format="json")
        self.cc.post(f"/api/missions/{self.mission_id}/confirm/")
        self.pc.post(f"/api/missions/{self.mission_id}/confirm/")
        self.assertEqual(self.cc.post(f"/api/missions/{self.mission_id}/start/").status_code, 403)

    def test_review_only_after_completion_and_once(self):
        self.assertEqual(
            self.cc.post(f"/api/missions/{self.mission_id}/review/", {"rating": 4}, format="json").status_code,
            400,
        )
        self._full_run_until_completed()
        self.assertEqual(
            self.cc.post(f"/api/missions/{self.mission_id}/review/", {"rating": 4}, format="json").status_code,
            201,
        )
        self.assertEqual(
            self.cc.post(f"/api/missions/{self.mission_id}/review/", {"rating": 2}, format="json").status_code,
            400,
        )

    def test_public_provider_profile_and_reviews(self):
        self._full_run_until_completed()
        self.cc.post(f"/api/missions/{self.mission_id}/review/", {"rating": 5, "comment": "top"}, format="json")

        anon = APIClient()
        prof = anon.get(f"/api/providers/{self.profile.id}/")
        self.assertEqual(prof.status_code, 200)
        self.assertEqual(float(prof.data["rating_avg"]), 5.0)
        self.assertIn("identite_verifiee", prof.data["badges"])

        revs = anon.get(f"/api/providers/{self.profile.id}/reviews/")
        self.assertEqual(revs.data["count"], 1)
        self.assertEqual(revs.data["results"][0]["comment"], "top")

    def test_provider_replies_to_review(self):
        self._full_run_until_completed()
        rid = self.cc.post(f"/api/missions/{self.mission_id}/review/", {"rating": 3}, format="json").data["id"]
        self.assertEqual(self.cc.post(f"/api/reviews/{rid}/reply/", {"reply": "merci"}, format="json").status_code, 403)
        r = self.pc.post(f"/api/reviews/{rid}/reply/", {"reply": "Merci pour votre retour"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["reply"], "Merci pour votre retour")
