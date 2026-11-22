from django.conf import settings
from django.db import transaction
from django.db.models import (
    Case,
    Count,
    IntegerField,
    Q,
    When,
)
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import ProviderProfile, User
from apps.ai import services as ai
from apps.catalog.models import ProviderCategory

from .models import (
    Conversation,
    Message,
    Mission,
    MissionPhoto,
    Notification,
    Quote,
    RequestPhoto,
    Review,
    ServiceRequest,
)
from .notifications import notify, notify_many
from .permissions import IsRequestOwner, IsVerifiedProvider
from .reputation import recompute_provider_reputation
from .serializers import (
    ConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
    MissionPhotoSerializer,
    MissionScheduleSerializer,
    MissionSerializer,
    NotificationSerializer,
    ProviderCategorySerializer,
    ProviderPublicProfileSerializer,
    ProviderSelfSerializer,
    QuoteCreateSerializer,
    QuoteSerializer,
    RequestFeedSerializer,
    RequestPhotoSerializer,
    ReviewCreateSerializer,
    ReviewSerializer,
    ServiceRequestSerializer,
)
from .text_filters import mask_contacts

MAX_PROVIDER_CATEGORIES = 5

MAX_PHOTOS = 4
DRAFT = ServiceRequest.Status.DRAFT


class ServiceRequestViewSet(viewsets.ModelViewSet):
    """Demandes de service — vue côté client (le propriétaire)."""

    serializer_class = ServiceRequestSerializer
    permission_classes = [IsAuthenticated, IsRequestOwner]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "category"]
    throttle_scope = "requests"

    def get_queryset(self):
        return (
            ServiceRequest.objects
            .filter(client=self.request.user)
            .select_related("category", "wilaya", "commune", "address", "target_provider__user")
            .prefetch_related("photos")
            .annotate(quotes_count=Count("quotes"))
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        if str(self.request.data.get("publish_now", "")).lower() in {"1", "true", "yes"}:
            self._publish(instance)

    def _assert_draft(self, instance):
        if instance.status != DRAFT:
            raise ValidationError("Seule une demande en brouillon peut être modifiée ou supprimée.")

    def perform_update(self, serializer):
        self._assert_draft(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_draft(instance)
        instance.delete()

    def _active_count(self):
        return ServiceRequest.objects.filter(
            client=self.request.user, status__in=ServiceRequest.ACTIVE_STATUSES
        ).count()

    def _publish(self, instance):
        if instance.status not in {DRAFT, ServiceRequest.Status.EXPIRED}:
            raise ValidationError("Cette demande ne peut pas être publiée.")
        if self._active_count() >= settings.MAX_ACTIVE_REQUESTS_PER_CLIENT:
            raise ValidationError(
                f"Limite de {settings.MAX_ACTIVE_REQUESTS_PER_CLIENT} demandes actives atteinte (RG-03)."
            )
        if not instance.photos.exists() and not instance.description:
            raise ValidationError("Ajoutez au moins une description ou une photo avant de publier.")
        instance.publish()
        if instance.target_provider_id:
            # demande ciblée : on prévient directement le professionnel choisi
            notify(
                instance.target_provider.user, "request_targeted", "Une demande de devis pour vous",
                f"{instance.client.full_name or 'Un client'} vous demande un devis : « {instance.title} ».",
                data={"request_id": instance.id},
            )

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        instance = self.get_object()
        self._publish(instance)
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def open_to_all(self, request, pk=None):
        """Demande ciblée -> ouverte à tous les pros du métier et de la zone."""
        instance = self.get_object()
        if instance.target_provider_id is None:
            raise ValidationError("Cette demande est déjà ouverte à tous les professionnels.")
        if instance.status not in {DRAFT, ServiceRequest.Status.PUBLISHED, ServiceRequest.Status.QUOTES_RECEIVED}:
            raise ValidationError("Cette demande n'accepte plus de devis.")
        instance.target_provider = None
        instance.save(update_fields=["target_provider", "updated_at"])
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        instance = self.get_object()
        if instance.status not in ServiceRequest.ACTIVE_STATUSES and instance.status != DRAFT:
            raise ValidationError("Cette demande ne peut plus être annulée.")
        instance.status = ServiceRequest.Status.CANCELLED
        instance.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def photos(self, request, pk=None):
        instance = self.get_object()
        if instance.status not in {DRAFT, *ServiceRequest.ACTIVE_STATUSES}:
            raise ValidationError("Demande clôturée : ajout de photo impossible.")
        if instance.photos.count() >= MAX_PHOTOS:
            raise ValidationError(f"Maximum {MAX_PHOTOS} photos par demande.")
        serializer = RequestPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(request=instance, order=instance.photos.count())
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"photos/(?P<photo_id>\d+)")
    def delete_photo(self, request, pk=None, photo_id=None):
        instance = self.get_object()
        deleted, _ = RequestPhoto.objects.filter(request=instance, pk=photo_id).delete()
        if not deleted:
            raise ValidationError("Photo introuvable.")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def quotes(self, request, pk=None):
        """Devis reçus pour cette demande — réservé au client propriétaire (comparaison)."""
        instance = self.get_object()  # IsRequestOwner appliqué
        qs = (
            instance.quotes.select_related("provider__provider_profile")
            .order_by("amount", "-created_at")
        )
        return Response(QuoteSerializer(qs, many=True).data)


# ==========================================================================
#  Prestataire : profil + catégories
# ==========================================================================
def _provider_profile(user):
    profile = getattr(user, "provider_profile", None)
    if profile is None:
        raise PermissionDenied("Aucun profil prestataire. Activez le rôle prestataire d'abord.")
    return profile


class ProviderProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProviderSelfSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return _provider_profile(self.request.user)


class ProviderCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ProviderCategory.objects.filter(provider__user=self.request.user)
            .select_related("category")
            .order_by("category__order", "category__name_fr")
        )

    def perform_create(self, serializer):
        profile = _provider_profile(self.request.user)
        if profile.categories.count() >= MAX_PROVIDER_CATEGORIES:
            raise ValidationError(f"Maximum {MAX_PROVIDER_CATEGORIES} catégories.")
        if profile.categories.filter(category=serializer.validated_data["category"]).exists():
            raise ValidationError("Catégorie déjà ajoutée.")
        serializer.save(provider=profile)


# ==========================================================================
#  Fil des demandes (prestataire vérifié)
# ==========================================================================
_URGENCY_RANK = Case(
    When(urgency=ServiceRequest.Urgency.IMMEDIATE, then=0),
    When(urgency=ServiceRequest.Urgency.TODAY, then=1),
    When(urgency=ServiceRequest.Urgency.THIS_WEEK, then=2),
    default=3,
    output_field=IntegerField(),
)


class RequestFeedViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = RequestFeedSerializer
    permission_classes = [IsAuthenticated, IsVerifiedProvider]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["category", "urgency"]

    def _profile(self):
        return _provider_profile(self.request.user)

    def get_queryset(self):
        profile = self._profile()
        cat_ids = list(profile.categories.values_list("category_id", flat=True))
        commune_ids = list(profile.service_communes.values_list("id", flat=True))
        # demandes ouvertes de mon métier et de ma zone + celles qui me sont adressées
        open_to_me = Q(target_provider__isnull=True, category_id__in=cat_ids, commune_id__in=commune_ids)
        targeted_to_me = Q(target_provider=profile)
        return (
            ServiceRequest.objects.filter(
                open_to_me | targeted_to_me,
                status__in=[ServiceRequest.Status.PUBLISHED, ServiceRequest.Status.QUOTES_RECEIVED],
            )
            .exclude(client=self.request.user)
            .select_related("category", "commune", "wilaya")
            .prefetch_related("photos")
            .annotate(u_rank=_URGENCY_RANK)
            .order_by("u_rank", "-published_at")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["provider"] = self._profile()
        if self.action == "list":
            page_ids = list(self.filter_queryset(self.get_queryset()).values_list("id", flat=True))
            ctx["quoted_ids"] = set(
                Quote.objects.filter(provider=self.request.user, request_id__in=page_ids)
                .values_list("request_id", flat=True)
            )
        return ctx


# ==========================================================================
#  Devis
# ==========================================================================
class QuoteViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "request"]

    def get_serializer_class(self):
        return QuoteCreateSerializer if self.action == "create" else QuoteSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsVerifiedProvider()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        return (
            Quote.objects.filter(Q(provider=user) | Q(request__client=user))
            .select_related("request", "provider__provider_profile")
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        req = self._get_open_request(request.data.get("request"))
        profile = _provider_profile(request.user)
        self._check_provider_can_serve(profile, req)
        if Quote.objects.filter(request=req, provider=request.user).exists():
            raise ValidationError("Vous avez déjà envoyé un devis pour cette demande.")

        s = QuoteCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        with transaction.atomic():
            quote = Quote.objects.create(
                request=req,
                provider=request.user,
                valid_until=Quote.default_validity(),
                **s.validated_data,
            )
            if req.status == ServiceRequest.Status.PUBLISHED:
                req.status = ServiceRequest.Status.QUOTES_RECEIVED
                req.save(update_fields=["status", "updated_at"])
            Conversation.objects.get_or_create(
                request=req, provider=request.user, defaults={"client": req.client}
            )
        notify(
            req.client, "quote_received", "Nouveau devis reçu",
            f"{request.user.full_name or 'Un prestataire'} a répondu à « {req.title} ».",
            data={"request_id": req.id, "quote_id": quote.id},
        )
        return Response(QuoteSerializer(quote).data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _get_open_request(request_id):
        try:
            req = ServiceRequest.objects.select_related("category", "commune").get(pk=request_id)
        except (ServiceRequest.DoesNotExist, TypeError, ValueError):
            raise ValidationError({"request": "Demande introuvable."})
        if req.status not in [ServiceRequest.Status.PUBLISHED, ServiceRequest.Status.QUOTES_RECEIVED]:
            raise ValidationError({"request": "Cette demande n'accepte plus de devis."})
        return req

    @staticmethod
    def _check_provider_can_serve(profile, req):
        if req.target_provider_id:
            # demande ciblée : seul le pro choisi répond, même hors de sa zone habituelle
            if req.target_provider_id != profile.id:
                raise ValidationError("Cette demande est réservée à un autre professionnel.")
            return
        if not profile.categories.filter(category_id=req.category_id).exists():
            raise ValidationError("Cette demande n'est pas dans vos catégories.")
        if not profile.service_communes.filter(id=req.commune_id).exists():
            raise ValidationError("Cette demande est hors de votre zone d'intervention.")

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        quote = self.get_object()
        if quote.provider_id != request.user.id:
            raise PermissionDenied("Ce devis n'est pas le vôtre.")
        if quote.status != Quote.Status.SENT:
            raise ValidationError("Ce devis ne peut plus être retiré.")
        quote.status = Quote.Status.WITHDRAWN
        quote.save(update_fields=["status", "updated_at"])
        return Response(QuoteSerializer(quote).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        quote = self.get_object()
        req = quote.request
        if req.client_id != request.user.id:
            raise PermissionDenied("Vous n'êtes pas le client de cette demande.")
        if quote.status != Quote.Status.SENT:
            raise ValidationError("Ce devis n'est plus disponible.")
        if quote.valid_until < timezone.now():
            raise ValidationError("Ce devis a expiré.")
        if req.status not in [ServiceRequest.Status.PUBLISHED, ServiceRequest.Status.QUOTES_RECEIVED]:
            raise ValidationError("Cette demande est déjà attribuée ou clôturée.")

        rejected_providers = list(
            req.quotes.exclude(pk=quote.pk).filter(status=Quote.Status.SENT)
            .values_list("provider_id", flat=True)
        )
        with transaction.atomic():
            quote.status = Quote.Status.ACCEPTED
            quote.save(update_fields=["status", "updated_at"])
            req.quotes.exclude(pk=quote.pk).filter(status=Quote.Status.SENT).update(
                status=Quote.Status.REJECTED
            )
            req.status = ServiceRequest.Status.ASSIGNED
            req.save(update_fields=["status", "updated_at"])
            mission = Mission.objects.create(
                request=req, quote=quote, provider=quote.provider, amount_due=quote.amount,
            )
            # Verrouille les conversations des prestataires non retenus (lecture seule).
            req.conversations.exclude(provider=quote.provider).update(is_locked=True)

        notify(
            quote.provider, "quote_accepted", "Devis accepté",
            f"Votre devis pour « {req.title} » a été accepté. Les coordonnées sont partagées.",
            data={"request_id": req.id, "mission_id": mission.id},
        )
        if rejected_providers:
            notify_many(
                User.objects.filter(id__in=rejected_providers),
                "quote_rejected", "Devis non retenu",
                f"Le client a choisi une autre offre pour « {req.title} ».",
                data={"request_id": req.id},
            )
        return Response(MissionSerializer(mission).data, status=status.HTTP_201_CREATED)


# ==========================================================================
#  Missions : suivi (RDV, démarrage, fin, paiement, avis)
# ==========================================================================
class MissionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]

    def get_queryset(self):
        user = self.request.user
        return (
            Mission.objects.filter(Q(provider=user) | Q(request__client=user))
            .select_related(
                "request__category", "request__wilaya", "request__commune",
                "request__address", "request__client", "provider__provider_profile", "quote",
            )
            .prefetch_related("request__photos", "photos")
            .order_by("-created_at")
        )

    # --- helpers -------------------------------------------------------
    def _is_client(self, mission):
        return mission.request.client_id == self.request.user.id

    def _is_provider(self, mission):
        return mission.provider_id == self.request.user.id

    def _reply(self, mission):
        mission.refresh_from_db()
        return Response(MissionSerializer(mission, context=self.get_serializer_context()).data)

    def _set_request_status(self, mission, new_status):
        mission.request.status = new_status
        mission.request.save(update_fields=["status", "updated_at"])

    # --- planification -----------------------------------------------
    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        mission = self.get_object()
        if mission.status not in (Mission.Status.PLANNED, Mission.Status.CONFIRMED):
            raise ValidationError("La mission ne peut plus être replanifiée.")
        s = MissionScheduleSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        mission.scheduled_at = s.validated_data["scheduled_at"]
        # une nouvelle proposition annule les confirmations précédentes
        mission.confirmed_by_client = self._is_client(mission)
        mission.confirmed_by_provider = self._is_provider(mission)
        mission.status = Mission.Status.PLANNED
        mission.save(update_fields=["scheduled_at", "confirmed_by_client", "confirmed_by_provider", "status", "updated_at"])
        other = mission.provider if self._is_client(mission) else mission.request.client
        notify(other, "mission_scheduled", "Proposition de rendez-vous",
               f"Créneau proposé pour « {mission.request.title} ».",
               data={"mission_id": mission.id})
        return self._reply(mission)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        mission = self.get_object()
        if not mission.scheduled_at:
            raise ValidationError("Aucun créneau proposé.")
        if self._is_client(mission):
            mission.confirmed_by_client = True
        if self._is_provider(mission):
            mission.confirmed_by_provider = True
        if mission.confirmed_by_client and mission.confirmed_by_provider:
            mission.status = Mission.Status.CONFIRMED
        mission.save(update_fields=["confirmed_by_client", "confirmed_by_provider", "status", "updated_at"])
        return self._reply(mission)

    # --- exécution ---------------------------------------------------
    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        mission = self.get_object()
        if not self._is_provider(mission):
            raise PermissionDenied("Seul le prestataire démarre la mission.")
        if mission.status not in (Mission.Status.PLANNED, Mission.Status.CONFIRMED):
            raise ValidationError("Mission non démarrable dans cet état.")
        mission.status = Mission.Status.IN_PROGRESS
        mission.started_at = timezone.now()
        mission.save(update_fields=["status", "started_at", "updated_at"])
        self._set_request_status(mission, ServiceRequest.Status.IN_PROGRESS)
        notify(mission.request.client, "mission_started", "Intervention démarrée",
               f"Le prestataire a démarré « {mission.request.title} ».", data={"mission_id": mission.id})
        return self._reply(mission)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        mission = self.get_object()
        if not self._is_provider(mission):
            raise PermissionDenied("Seul le prestataire clôture l'intervention.")
        if mission.status != Mission.Status.IN_PROGRESS:
            raise ValidationError("La mission n'est pas en cours.")
        mission.status = Mission.Status.COMPLETED
        mission.ended_at = timezone.now()
        mission.save(update_fields=["status", "ended_at", "updated_at"])
        self._set_request_status(mission, ServiceRequest.Status.COMPLETED)
        recompute_provider_reputation(mission.provider)
        notify(mission.request.client, "mission_completed", "Intervention terminée",
               f"« {mission.request.title} » est terminée. Confirmez le paiement puis laissez un avis.",
               data={"mission_id": mission.id})
        return self._reply(mission)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def photos(self, request, pk=None):
        mission = self.get_object()
        if not self._is_provider(mission):
            raise PermissionDenied("Seul le prestataire ajoute des photos de mission.")
        s = MissionPhotoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if s.validated_data["kind"] not in (MissionPhoto.Kind.BEFORE, MissionPhoto.Kind.AFTER):
            raise ValidationError("kind invalide.")
        s.save(mission=mission)
        return Response(s.data, status=status.HTTP_201_CREATED)

    # --- paiement (espèces) ----------------------------------------
    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        mission = self.get_object()
        if not self._is_client(mission):
            raise PermissionDenied("Seul le client confirme avoir payé.")
        if mission.status not in (Mission.Status.COMPLETED, Mission.Status.PAID):
            raise ValidationError("La mission n'est pas terminée.")
        mission.paid_at = mission.paid_at or timezone.now()
        if mission.payment_confirmed_by_provider:
            mission.status = Mission.Status.PAID
        mission.save(update_fields=["paid_at", "status", "updated_at"])
        notify(mission.provider, "payment_declared", "Paiement déclaré",
               f"Le client indique avoir payé « {mission.request.title} ».", data={"mission_id": mission.id})
        return self._reply(mission)

    @action(detail=True, methods=["post"], url_path="confirm-payment")
    def confirm_payment(self, request, pk=None):
        mission = self.get_object()
        if not self._is_provider(mission):
            raise PermissionDenied("Seul le prestataire confirme la réception du paiement.")
        mission.payment_confirmed_by_provider = True
        if mission.paid_at:
            mission.status = Mission.Status.PAID
        mission.save(update_fields=["payment_confirmed_by_provider", "status", "updated_at"])
        return self._reply(mission)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        mission = self.get_object()
        if mission.status not in (Mission.Status.PLANNED, Mission.Status.CONFIRMED):
            raise ValidationError("Une mission démarrée ne peut plus être annulée ici (ouvrir un litige).")
        late = (
            self._is_client(mission)
            and mission.scheduled_at
            and (mission.scheduled_at - timezone.now()).total_seconds() < 2 * 3600
        )
        with transaction.atomic():
            mission.status = Mission.Status.CANCELLED
            mission.save(update_fields=["status", "updated_at"])
            self._set_request_status(mission, ServiceRequest.Status.CANCELLED)
            mission.quote.status = Quote.Status.REJECTED
            mission.quote.save(update_fields=["status", "updated_at"])
        other = mission.provider if self._is_client(mission) else mission.request.client
        body = "Annulation tardive (< 2 h)." if late else "La mission a été annulée."
        notify(other, "mission_cancelled", "Mission annulée", body, data={"mission_id": mission.id})
        return self._reply(mission)

    # --- évaluation (client -> prestataire) -----------------------
    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        mission = self.get_object()
        if not self._is_client(mission):
            raise PermissionDenied("Seul le client évalue le prestataire.")
        if mission.status not in (Mission.Status.COMPLETED, Mission.Status.PAID):
            raise ValidationError("La mission doit être terminée.")
        if hasattr(mission, "review"):
            raise ValidationError("Vous avez déjà laissé un avis.")
        s = ReviewCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        # modération IA : un avis injurieux / frauduleux attend une validation manuelle
        needs_review, verdict = ai.review_needs_moderation(s.validated_data.get("comment", ""))
        review = Review.objects.create(
            mission=mission, author=mission.request.client, target=mission.provider,
            moderation_status=Review.Moderation.PENDING if needs_review else Review.Moderation.APPROVED,
            **s.validated_data,
        )
        ai.record_review_verdict(review, verdict)
        self._set_request_status(mission, ServiceRequest.Status.EVALUATED)
        recompute_provider_reputation(mission.provider)
        notify(mission.provider, "review_received", "Nouvel avis",
               f"{review.rating}★ pour « {mission.request.title} ».", data={"mission_id": mission.id})
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ReviewReplyView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        try:
            review = Review.objects.select_related("target").get(pk=pk)
        except Review.DoesNotExist:
            raise ValidationError("Avis introuvable.")
        if review.target_id != request.user.id:
            raise PermissionDenied("Vous ne pouvez répondre qu'à vos propres avis.")
        if review.reply:
            raise ValidationError("Une réponse existe déjà.")
        reply = (request.data.get("reply") or "").strip()
        if not reply:
            raise ValidationError({"reply": "Réponse vide."})
        review.reply = reply
        review.save(update_fields=["reply"])
        return Response(ReviewSerializer(review).data)


# ==========================================================================
#  Fiche prestataire publique
# ==========================================================================
def _int_param(request, name):
    value = request.query_params.get(name)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError({name: "Doit être un nombre entier."})


class PublicProviderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Annuaire public des prestataires validés.

    Filtres de la liste (tous facultatifs) :
      ?category=<id>   métier (une famille inclut ses prestations)
      ?wilaya=<id>     wilaya de base ou wilaya d'une commune d'intervention
      ?commune=<id>    commune d'intervention (ou wilaya de base de cette commune)
      ?available=1     seulement les prestataires disponibles
      ?search=<texte>  nom, nom commercial, présentation
      ?ordering=-rating_avg | -missions_count | -reviews_count
    """

    permission_classes = [AllowAny]
    serializer_class = ProviderPublicProfileSerializer
    search_fields = ("user__full_name", "business_name", "bio")
    ordering_fields = ("rating_avg", "missions_count", "reviews_count", "years_experience")
    ordering = ("-is_available", "-rating_avg", "-reviews_count", "-missions_count", "id")

    def get_queryset(self):
        qs = (
            ProviderProfile.objects.filter(
                verification_status=ProviderProfile.Verification.APPROVED,
                user__is_active=True,
            )
            .select_related("user", "base_wilaya")
            .prefetch_related("categories__category")
        )
        if self.action != "list":
            return qs

        category = _int_param(self.request, "category")
        if category is not None:
            qs = qs.filter(Q(categories__category_id=category) | Q(categories__category__parent_id=category))

        wilaya = _int_param(self.request, "wilaya")
        if wilaya is not None:
            qs = qs.filter(Q(base_wilaya_id=wilaya) | Q(service_communes__wilaya_id=wilaya))

        commune = _int_param(self.request, "commune")
        if commune is not None:
            qs = qs.filter(Q(service_communes__id=commune) | Q(base_wilaya__communes__id=commune))

        if self.request.query_params.get("available") in ("1", "true", "True"):
            qs = qs.filter(is_available=True)

        # les jointures ci-dessus peuvent dupliquer un prestataire
        return qs.distinct()

    @action(detail=True, methods=["get"])
    def reviews(self, request, pk=None):
        profile = self.get_object()
        qs = (
            Review.objects.filter(
                target=profile.user, moderation_status=Review.Moderation.APPROVED
            )
            .select_related("author")
            .order_by("-created_at")
        )
        page = self.paginate_queryset(qs)
        data = ReviewSerializer(page if page is not None else qs, many=True).data
        return self.get_paginated_response(data) if page is not None else Response(data)


# ==========================================================================
#  Messagerie
# ==========================================================================
class ConversationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects.filter(Q(client=user) | Q(provider=user))
            .select_related("request", "client", "provider__provider_profile")
            .prefetch_related("messages")
        )

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        conv = self.get_object()
        if request.method == "GET":
            qs = conv.messages.select_related("conversation").order_by("created_at")
            conv.messages.filter(read_at__isnull=True).exclude(sender=request.user).update(
                read_at=timezone.now()
            )
            page = self.paginate_queryset(qs)
            data = MessageSerializer(page if page is not None else qs, many=True).data
            return self.get_paginated_response(data) if page is not None else Response(data)

        # POST : envoyer un message
        if conv.is_locked:
            raise ValidationError("Conversation verrouillée (une autre offre a été retenue).")
        if conv.request.status in (
            ServiceRequest.Status.CANCELLED, ServiceRequest.Status.EXPIRED, ServiceRequest.Status.CLOSED,
        ):
            raise ValidationError("Cette demande est clôturée.")

        s = MessageCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        body = s.validated_data.get("body", "")
        filtered, was_filtered = (body, False)
        if body and not conv.contacts_unlocked:
            filtered, was_filtered = mask_contacts(body)

        msg = Message.objects.create(
            conversation=conv,
            sender=request.user,
            type=s.validated_data.get("type", Message.Type.TEXT),
            body=filtered,
            body_raw=body if was_filtered else "",
            was_filtered=was_filtered,
            attachment=s.validated_data.get("attachment"),
        )
        conv.last_message_at = msg.created_at
        conv.save(update_fields=["last_message_at"])
        ai.moderate_message_async(msg, conv.contacts_unlocked)

        other = conv.provider if request.user.id == conv.client_id else conv.client
        notify(
            other, "new_message", "Nouveau message",
            f"{request.user.full_name or 'Message'} · {conv.request.title}",
            data={"conversation_id": conv.id, "request_id": conv.request_id},
        )
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        conv = self.get_object()
        updated = conv.messages.filter(read_at__isnull=True).exclude(sender=request.user).update(
            read_at=timezone.now()
        )
        return Response({"marked_read": updated})


class MessageFlagView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        try:
            msg = Message.objects.select_related("conversation").get(pk=pk)
        except Message.DoesNotExist:
            raise ValidationError("Message introuvable.")
        if not msg.conversation.involves(request.user):
            raise PermissionDenied("Accès refusé.")
        msg.flagged = True
        msg.save(update_fields=["flagged"])
        return Response({"flagged": True})


# ==========================================================================
#  Notifications & appareils (push)
# ==========================================================================
class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_read", "type"]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        return Response({"unread": self.get_queryset().filter(is_read=False).count()})

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        n = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"marked_read": n})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        Notification.objects.filter(pk=pk, recipient=request.user).update(is_read=True)
        return Response({"is_read": True})


class DeviceRegisterView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        if not token:
            raise ValidationError({"token": "Jeton manquant."})
        platform = request.data.get("platform", "android")
        obj, _ = request.user.devices.update_or_create(
            token=token, defaults={"platform": platform}
        )
        return Response({"registered": True}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        token = (request.data.get("token") or "").strip()
        request.user.devices.filter(token=token).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
