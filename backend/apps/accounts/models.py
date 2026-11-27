from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra):
        if not phone:
            raise ValueError(_("Le numéro de téléphone est obligatoire."))
        user = self.model(phone=phone, **extra)
        user.set_password(password)  # password=None -> mot de passe inutilisable
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        extra.setdefault("phone_verified", True)
        if extra.get("is_staff") is not True or extra.get("is_superuser") is not True:
            raise ValueError(_("Un superuser doit avoir is_staff=True et is_superuser=True."))
        return self.create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Language(models.TextChoices):
        FR = "fr", _("Français")
        AR = "ar", _("العربية")

    phone = PhoneNumberField(_("téléphone"), unique=True)
    email = models.EmailField(_("email"), blank=True)
    full_name = models.CharField(_("nom complet"), max_length=150, blank=True)
    photo = models.ImageField(_("photo"), upload_to="users/", blank=True, null=True)

    is_client = models.BooleanField(_("est client"), default=True)
    is_provider = models.BooleanField(_("est prestataire"), default=False)
    phone_verified = models.BooleanField(_("téléphone vérifié"), default=False)
    language = models.CharField(_("langue"), max_length=2, choices=Language.choices, default=Language.FR)

    is_active = models.BooleanField(_("actif"), default=True)
    is_staff = models.BooleanField(_("accès admin"), default=False)
    date_joined = models.DateTimeField(_("date d'inscription"), default=timezone.now)
    last_seen_at = models.DateTimeField(_("dernière activité"), null=True, blank=True)

    # preuve du consentement (loi 18-07) : version de la politique acceptée et date
    privacy_version = models.CharField(_("politique de confidentialité acceptée"), max_length=20, blank=True)
    privacy_accepted_at = models.DateTimeField(_("acceptée le"), null=True, blank=True)

    def accept_privacy(self, version, save=True):
        self.privacy_version = version
        self.privacy_accepted_at = timezone.now()
        if save:
            self.save(update_fields=["privacy_version", "privacy_accepted_at"])

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("utilisateur")
        verbose_name_plural = _("utilisateurs")
        ordering = ("-date_joined",)

    def __str__(self):
        return self.full_name or str(self.phone)


class ClientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_profile")
    reliability_score = models.DecimalField(_("score de fiabilité"), max_digits=3, decimal_places=1, default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("profil client")
        verbose_name_plural = _("profils clients")

    def __str__(self):
        return f"Client · {self.user}"


class ProviderProfile(models.Model):
    class LegalStatus(models.TextChoices):
        AUTO = "auto_entrepreneur", _("Auto-entrepreneur")
        ARTISAN = "artisan", _("Artisan inscrit")
        COMPANY = "entreprise", _("Entreprise")
        UNDECLARED = "non_declare", _("Non déclaré")

    class Verification(models.TextChoices):
        PENDING = "pending", _("En attente")
        APPROVED = "approved", _("Validé")
        REJECTED = "rejected", _("Refusé")

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="provider_profile")
    business_name = models.CharField(_("raison sociale"), max_length=150, blank=True)
    legal_status = models.CharField(_("statut juridique"), max_length=20, choices=LegalStatus.choices, default=LegalStatus.UNDECLARED)
    rc_number = models.CharField(_("n° registre de commerce"), max_length=50, blank=True)
    nif = models.CharField("NIF", max_length=50, blank=True)
    bio = models.TextField(_("description"), blank=True)
    years_experience = models.PositiveSmallIntegerField(_("années d'expérience"), default=0)

    base_wilaya = models.ForeignKey(
        "locations.Wilaya", null=True, blank=True, on_delete=models.SET_NULL, related_name="based_providers"
    )
    service_communes = models.ManyToManyField("locations.Commune", blank=True, related_name="providers")
    radius_km = models.PositiveSmallIntegerField(_("rayon de déplacement (km)"), default=10)
    latitude = models.DecimalField(_("latitude (base)"), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(_("longitude (base)"), max_digits=9, decimal_places=6, null=True, blank=True)

    verification_status = models.CharField(
        _("statut de vérification"), max_length=10, choices=Verification.choices, default=Verification.PENDING
    )
    verification_notes = models.TextField(_("notes de vérification (interne)"), blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    rating_avg = models.DecimalField(_("note moyenne"), max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField(default=0)
    missions_count = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(_("disponible"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("profil prestataire")
        verbose_name_plural = _("profils prestataires")

    def __str__(self):
        return f"Prestataire · {self.business_name or self.user}"

    @property
    def is_verified(self):
        return self.verification_status == self.Verification.APPROVED


class PortfolioPhoto(models.Model):
    """Photo d'un travail réalisé par l'artisan (galerie visible sur sa fiche publique)."""

    MAX_PER_PROVIDER = 12

    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name="portfolio")
    image = models.ImageField(_("photo"), upload_to="portfolio/%Y/%m/")
    caption = models.CharField(_("légende"), max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("réalisation")
        verbose_name_plural = _("réalisations")
        ordering = ("-created_at",)

    def __str__(self):
        return self.caption or f"Réalisation #{self.pk}"


class DailyVisit(models.Model):
    """Une ligne par personne, par jour et par application : statistiques de fréquentation.

    Donnée minimale (pas d'heure précise, pas de position) ; effacée après 13 mois."""

    class App(models.TextChoices):
        CLIENT = "client", _("BRICOOL (client)")
        PRO = "pro", _("BRICOOL Pro (artisan)")
        OTHER = "", _("Autre / ancienne version")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="visits")
    day = models.DateField(_("jour"), db_index=True)
    app = models.CharField(_("application"), max_length=8, choices=App.choices, blank=True, default="")
    hits = models.PositiveIntegerField(_("requêtes"), default=1)

    class Meta:
        verbose_name = _("visite")
        verbose_name_plural = _("visites")
        ordering = ("-day",)
        constraints = [models.UniqueConstraint(fields=["user", "day", "app"], name="uniq_visite_par_jour")]

    def __str__(self):
        return f"{self.user} · {self.day} · {self.app or 'autre'}"


class PhoneOTP(models.Model):
    class Purpose(models.TextChoices):
        REGISTRATION = "registration", _("Inscription")
        LOGIN = "login", _("Connexion")
        RESET = "password_reset", _("Réinitialisation")

    phone = PhoneNumberField(_("téléphone"))
    code_hash = models.CharField(max_length=128)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("code OTP")
        verbose_name_plural = _("codes OTP")
        indexes = [models.Index(fields=["phone", "purpose", "-created_at"])]

    def __str__(self):
        return f"OTP {self.phone} ({self.purpose})"

    @property
    def is_valid(self):
        return (
            self.consumed_at is None
            and self.attempts < settings.OTP_MAX_ATTEMPTS
            and timezone.now() < self.expires_at
        )

    @classmethod
    def default_expiry(cls):
        return timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS)


class DeviceToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, default="android")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("jeton d'appareil (push)")
        verbose_name_plural = _("jetons d'appareils (push)")

    def __str__(self):
        return f"{self.user} · {self.platform}"
