from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ServiceRequest(models.Model):
    """Cœur du système : une demande publiée par un client."""

    class Urgency(models.TextChoices):
        IMMEDIATE = "immediate", _("Immédiat (< 2 h)")
        TODAY = "today", _("Aujourd'hui")
        THIS_WEEK = "this_week", _("Cette semaine")
        FLEXIBLE = "flexible", _("Flexible")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Brouillon")
        PUBLISHED = "published", _("Publiée")
        QUOTES_RECEIVED = "quotes_received", _("Devis reçus")
        ASSIGNED = "assigned", _("Attribuée")
        IN_PROGRESS = "in_progress", _("En cours")
        COMPLETED = "completed", _("Terminée")
        EVALUATED = "evaluated", _("Évaluée")
        CLOSED = "closed", _("Clôturée")
        CANCELLED = "cancelled", _("Annulée")
        EXPIRED = "expired", _("Expirée")

    ACTIVE_STATUSES = (
        Status.PUBLISHED, Status.QUOTES_RECEIVED, Status.ASSIGNED, Status.IN_PROGRESS,
    )

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_requests")
    category = models.ForeignKey("catalog.Category", on_delete=models.PROTECT, related_name="requests")
    title = models.CharField(_("titre"), max_length=140)
    description = models.TextField(_("description"))

    address = models.ForeignKey(
        "locations.Address", null=True, blank=True, on_delete=models.SET_NULL, related_name="requests"
    )
    # instantané de localisation (l'adresse peut être supprimée/modifiée plus tard)
    wilaya = models.ForeignKey("locations.Wilaya", on_delete=models.PROTECT, related_name="requests")
    commune = models.ForeignKey("locations.Commune", on_delete=models.PROTECT, related_name="requests")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    urgency = models.CharField(_("urgence"), max_length=12, choices=Urgency.choices, default=Urgency.THIS_WEEK)
    budget_min = models.DecimalField(_("budget min (DA)"), max_digits=10, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(_("budget max (DA)"), max_digits=10, decimal_places=2, null=True, blank=True)

    status = models.CharField(_("statut"), max_length=16, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(_("date de publication"), null=True, blank=True)
    expires_at = models.DateTimeField(_("date d'expiration"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("demande de service")
        verbose_name_plural = _("demandes de service")
        ordering = ("-published_at", "-created_at")
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["status", "commune"]),
        ]

    def __str__(self):
        return f"#{self.pk} {self.title}"

    def publish(self):
        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()
        self.expires_at = self.published_at + timedelta(days=settings.REQUEST_EXPIRY_DAYS)
        self.save(update_fields=["status", "published_at", "expires_at", "updated_at"])

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES


class RequestDispatch(models.Model):
    """Un bricoleur à qui la demande a été envoyée (le plus proche d'abord, par vagues)."""

    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="dispatches")
    provider = models.ForeignKey(
        "accounts.ProviderProfile", on_delete=models.CASCADE, related_name="dispatches"
    )
    wave = models.PositiveSmallIntegerField(_("vague"), default=1)
    distance_km = models.DecimalField(
        _("distance (km)"), max_digits=6, decimal_places=1, null=True, blank=True,
        help_text=_("Vide si la position GPS manque : envoi selon la commune."),
    )
    sent_at = models.DateTimeField(_("envoyée le"), default=timezone.now)

    class Meta:
        verbose_name = _("envoi à un bricoleur")
        verbose_name_plural = _("envois aux bricoleurs")
        ordering = ("wave", "distance_km")
        constraints = [
            models.UniqueConstraint(fields=["request", "provider"], name="uniq_envoi_par_prestataire"),
        ]

    def __str__(self):
        return f"Demande {self.request_id} → {self.provider_id} (vague {self.wave})"


class RequestPhoto(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="requests/%Y/%m/")
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("photo de demande")
        verbose_name_plural = _("photos de demande")
        ordering = ("order", "id")


class Quote(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", _("Envoyé")
        ACCEPTED = "accepted", _("Accepté")
        REJECTED = "rejected", _("Refusé")
        EXPIRED = "expired", _("Expiré")
        WITHDRAWN = "withdrawn", _("Retiré")

    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="quotes")
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quotes")
    amount = models.DecimalField(_("montant (DA)"), max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    lead_time_days = models.PositiveSmallIntegerField(_("délai d'intervention (jours)"), default=1)
    estimated_duration = models.CharField(_("durée estimée"), max_length=60, blank=True)
    message = models.TextField(_("message"), blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SENT)
    valid_until = models.DateTimeField(_("valable jusqu'au"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("devis")
        verbose_name_plural = _("devis")
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=["request", "provider"], name="uniq_quote_par_prestataire"),
        ]

    def __str__(self):
        return f"Devis #{self.pk} · {self.amount} DA"

    @classmethod
    def default_validity(cls):
        return timezone.now() + timedelta(hours=settings.QUOTE_VALIDITY_HOURS)


class Mission(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", _("Planifiée")
        CONFIRMED = "confirmed", _("Confirmée (2 parties)")
        IN_PROGRESS = "in_progress", _("En cours")
        COMPLETED = "completed", _("Terminée")
        PAID = "paid", _("Payée")
        CANCELLED = "cancelled", _("Annulée")

    request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name="mission")
    quote = models.OneToOneField(Quote, on_delete=models.PROTECT, related_name="mission")
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="missions")

    scheduled_at = models.DateTimeField(_("date planifiée"), null=True, blank=True)
    confirmed_by_client = models.BooleanField(default=False)
    confirmed_by_provider = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLANNED)

    amount_due = models.DecimalField(_("montant dû (DA)"), max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(_("payée le"), null=True, blank=True)
    payment_confirmed_by_provider = models.BooleanField(_("paiement confirmé par le prestataire"), default=False)
    payment_method = models.CharField(_("mode de paiement"), max_length=20, default="cash")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("mission")
        verbose_name_plural = _("missions")
        ordering = ("-created_at",)

    def __str__(self):
        return f"Mission #{self.pk} · {self.request.title}"


class MissionPhoto(models.Model):
    class Kind(models.TextChoices):
        BEFORE = "before", _("Avant")
        AFTER = "after", _("Après")

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="photos")
    kind = models.CharField(max_length=6, choices=Kind.choices)
    image = models.ImageField(upload_to="missions/%Y/%m/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("photo de mission")
        verbose_name_plural = _("photos de mission")


class Conversation(models.Model):
    """Fil de discussion entre le client et UN prestataire, rattaché à une demande."""

    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="conversations")
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_conversations"
    )
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="provider_conversations"
    )
    is_locked = models.BooleanField(
        _("verrouillée"), default=False,
        help_text=_("Lecture seule : une autre offre a été retenue ou la demande est close."),
    )
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("conversation")
        verbose_name_plural = _("conversations")
        ordering = ("-last_message_at", "-created_at")
        constraints = [
            models.UniqueConstraint(fields=["request", "provider"], name="uniq_conversation_par_prestataire"),
        ]

    def __str__(self):
        return f"Conv #{self.pk} · demande {self.request_id}"

    def involves(self, user):
        return user.id in (self.client_id, self.provider_id)

    UNLOCKED_STATUSES = (
        ServiceRequest.Status.ASSIGNED, ServiceRequest.Status.IN_PROGRESS,
        ServiceRequest.Status.COMPLETED, ServiceRequest.Status.EVALUATED,
        ServiceRequest.Status.CLOSED,
    )

    @property
    def contacts_unlocked(self):
        """RG-05 : numéros/liens filtrés tant que la demande n'est pas attribuée à CE prestataire."""
        if self.request.status not in self.UNLOCKED_STATUSES:
            return False
        mission = getattr(self.request, "mission", None)
        return mission is not None and mission.provider_id == self.provider_id


class Message(models.Model):
    class Type(models.TextChoices):
        TEXT = "text", _("Texte")
        PHOTO = "photo", _("Photo")
        SYSTEM = "system", _("Système")

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    type = models.CharField(max_length=8, choices=Type.choices, default=Type.TEXT)
    body = models.TextField(_("contenu"), blank=True)
    body_raw = models.TextField(_("contenu original (avant filtrage)"), blank=True)
    was_filtered = models.BooleanField(default=False)
    attachment = models.ImageField(upload_to="messages/%Y/%m/", blank=True, null=True)
    read_at = models.DateTimeField(null=True, blank=True)
    flagged = models.BooleanField(_("signalé"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")
        ordering = ("created_at",)
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self):
        return f"Msg #{self.pk} (conv {self.conversation_id})"


class Review(models.Model):
    """MVP : évaluation à sens unique (client -> prestataire)."""

    class Moderation(models.TextChoices):
        APPROVED = "approved", _("Publié")
        PENDING = "pending", _("En attente")
        REJECTED = "rejected", _("Rejeté")

    mission = models.OneToOneField(Mission, on_delete=models.CASCADE, related_name="review")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_written")
    target = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_received")
    rating = models.PositiveSmallIntegerField(_("note"), validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(_("commentaire"), blank=True)
    moderation_status = models.CharField(max_length=10, choices=Moderation.choices, default=Moderation.APPROVED)
    reply = models.TextField(_("réponse du prestataire"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("avis")
        verbose_name_plural = _("avis")
        ordering = ("-created_at",)

    def __str__(self):
        return f"Avis {self.rating}★ · {self.target}"


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=40)
    title = models.CharField(max_length=140)
    body = models.CharField(max_length=255, blank=True)
    channel = models.CharField(max_length=10, default="push")
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["recipient", "is_read", "-created_at"])]

    def __str__(self):
        return f"{self.type} → {self.recipient}"


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_entries"
    )
    action = models.CharField(max_length=80)
    target_type = models.CharField(max_length=80, blank=True)
    target_id = models.CharField(max_length=40, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("entrée du journal d'audit")
        verbose_name_plural = _("journal d'audit")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} · {self.action}"
