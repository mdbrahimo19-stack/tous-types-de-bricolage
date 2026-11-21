import json
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import ClientProfile, User
from apps.catalog.models import Category
from apps.locations.models import Commune, Wilaya
from apps.marketplace.models import AuditLog, Conversation, Message, Quote, ServiceRequest

from . import services

NO_THROTTLE = {"DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}}


def fake_response(payload, stop_reason="end_turn"):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(
        stop_reason=stop_reason,
        stop_details=None,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
    )


def patch_claude(*responses):
    """Remplace le client Anthropic ; renvoie le mock de messages.create."""
    create = mock.Mock(side_effect=list(responses))
    fake = SimpleNamespace(messages=SimpleNamespace(create=create))
    patcher = mock.patch("apps.ai.client._client", return_value=fake)
    return patcher, create


@override_settings(AI_ENABLED=True, REST_FRAMEWORK=NO_THROTTLE)
class AIEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.wilaya = Wilaya.objects.create(code="16", name_fr="Alger", is_active=True)
        cls.commune = Commune.objects.create(wilaya=cls.wilaya, name_fr="Kouba")
        cls.root = Category.objects.create(name_fr="Plomberie", name_ar="سباكة", order=1)
        cls.leak = Category.objects.create(
            name_fr="Fuite d'eau", parent=cls.root, price_min=1500, price_max=5000
        )
        cls.user = User.objects.create_user(phone="+213661000001", phone_verified=True, full_name="Client")
        ClientProfile.objects.create(user=cls.user)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def test_draft_request_returns_structured_draft(self):
        draft = {
            "category_id": self.leak.id, "title": "Fuite sous l'évier",
            "description": "Fuite sous l'évier de la cuisine.", "urgency": "today",
            "budget_min": None, "budget_max": None,
            "missing_info": ["Depuis quand ?", "Eau coupée ?", "Étage ?", "En trop"],
            "language": "fr",
        }
        patcher, create = patch_claude(fake_response(draft))
        with patcher:
            resp = self.api.post("/api/ai/draft-request/", {"text": "3andi fuite f la cuisine"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["category_id"], self.leak.id)
        self.assertEqual(len(resp.data["missing_info"]), 3)
        kwargs = create.call_args.kwargs
        self.assertIn(f"{self.leak.id} | Plomberie › Fuite d'eau", kwargs["system"])
        self.assertEqual(kwargs["output_config"]["format"]["type"], "json_schema")

    def test_draft_request_drops_unknown_category(self):
        draft = {
            "category_id": 99999, "title": "x", "description": "y", "urgency": "flexible",
            "budget_min": None, "budget_max": None, "missing_info": [], "language": "ar",
        }
        patcher, _ = patch_claude(fake_response(draft))
        with patcher:
            resp = self.api.post("/api/ai/draft-request/", {"text": "عندي مشكل في الضو"}, format="json")
        self.assertIsNone(resp.data["category_id"])

    def test_price_estimate_uses_accepted_quotes_and_orders_bounds(self):
        req = ServiceRequest.objects.create(
            client=self.user, category=self.leak, title="t", description="d",
            wilaya=self.wilaya, commune=self.commune,
        )
        provider = User.objects.create_user(phone="+213661000002", phone_verified=True, is_provider=True)
        Quote.objects.create(request=req, provider=provider, amount=3000,
                             status=Quote.Status.ACCEPTED, valid_until=Quote.default_validity())
        estimate = {"min_da": 4000, "max_da": 2000, "confidence": "medium", "explanation": "ok"}
        patcher, create = patch_claude(fake_response(estimate))
        with patcher:
            resp = self.api.post("/api/ai/price-estimate/", {
                "category": self.leak.id, "description": "Fuite sous évier", "wilaya": self.wilaya.id,
            }, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual((resp.data["min_da"], resp.data["max_da"]), (2000, 4000))
        self.assertEqual(resp.data["based_on_quotes"], 1)
        prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn("médiane 3000 DA", prompt)
        self.assertIn("1500.00 – 5000.00 DA", prompt)

    def test_support_chat(self):
        patcher, create = patch_claude(fake_response("Le paiement se fait en espèces."))
        history = [
            {"role": "assistant", "content": "Bonjour !"},  # retiré : doit commencer par l'utilisateur
            {"role": "user", "content": "Comment je paie ?"},
        ]
        with patcher:
            resp = self.api.post("/api/ai/support/", {"messages": history}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["reply"], "Le paiement se fait en espèces.")
        self.assertEqual(create.call_args.kwargs["messages"][0]["role"], "user")

    def test_support_rejects_history_ending_with_assistant(self):
        resp = self.api.post("/api/ai/support/", {"messages": [
            {"role": "user", "content": "salut"}, {"role": "assistant", "content": "salut"},
        ]}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_refusal_returns_503(self):
        patcher, _ = patch_claude(fake_response("", stop_reason="refusal"))
        with patcher:
            resp = self.api.post("/api/ai/support/", {"messages": [{"role": "user", "content": "x"}]}, format="json")
        self.assertEqual(resp.status_code, 503)

    @override_settings(AI_ENABLED=False)
    def test_disabled_returns_503(self):
        resp = self.api.post("/api/ai/draft-request/", {"text": "fuite d'eau"}, format="json")
        self.assertEqual(resp.status_code, 503)

    def test_requires_authentication(self):
        resp = APIClient().post("/api/ai/draft-request/", {"text": "fuite d'eau"}, format="json")
        self.assertEqual(resp.status_code, 401)


@override_settings(AI_ENABLED=True)
class ModerationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        wilaya = Wilaya.objects.create(code="16", name_fr="Alger")
        commune = Commune.objects.create(wilaya=wilaya, name_fr="Kouba")
        cat = Category.objects.create(name_fr="Peinture")
        cls.client_user = User.objects.create_user(phone="+213661000003", phone_verified=True)
        cls.provider = User.objects.create_user(phone="+213661000004", phone_verified=True, is_provider=True)
        req = ServiceRequest.objects.create(
            client=cls.client_user, category=cat, title="t", description="d", wilaya=wilaya, commune=commune,
        )
        cls.conv = Conversation.objects.create(request=req, client=cls.client_user, provider=cls.provider)

    def test_review_flagged_goes_to_manual_moderation(self):
        verdict = {"allowed": False, "categories": ["insult"], "reason": "Insulte."}
        patcher, _ = patch_claude(fake_response(verdict))
        with patcher:
            needs_review, got = services.review_needs_moderation("espèce de voleur")
        self.assertTrue(needs_review)
        self.assertEqual(got["categories"], ["insult"])

    def test_moderation_fails_open_when_api_down(self):
        with mock.patch("apps.ai.services.ask", side_effect=services.AIUnavailable("down")):
            needs_review, _ = services.review_needs_moderation("Très bon travail")
        self.assertFalse(needs_review)

    def test_message_moderation_flags_and_audits(self):
        msg = Message.objects.create(conversation=self.conv, sender=self.provider, body="ajoute moi sur insta")
        verdict = {"allowed": False, "categories": ["contact_bypass"], "reason": "Contournement."}
        patcher, create = patch_claude(fake_response(verdict))
        with patcher, mock.patch("apps.ai.services.close_old_connections"):
            services._moderate_message(msg.pk, contacts_unlocked=False)
        msg.refresh_from_db()
        self.assertTrue(msg.flagged)
        log = AuditLog.objects.get(action="ai_moderation", target_id=str(msg.pk))
        self.assertEqual(log.changes["categories"], ["contact_bypass"])
        self.assertIn("<contenu>\najoute moi sur insta\n</contenu>", create.call_args.kwargs["messages"][0]["content"])
