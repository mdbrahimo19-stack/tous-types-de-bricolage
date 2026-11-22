"""Points des bricoleurs.

Chaque client qui accepte le devis d'un bricoleur lui coûte POINTS_PER_CONTACT points
(1 point = POINT_VALUE_DA DA). Les POINTS_WELCOME_FREE premiers points sont offerts.
Quand les points dus atteignent POINTS_BLOCK_AT, le compte est bloqué jusqu'à ce que
le bricoleur paie par BaridiMob et que l'administrateur valide la capture du paiement.
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def _welcome_points():
    return settings.POINTS_WELCOME_FREE


class PointsAccount(models.Model):
    provider = models.OneToOneField(
        "accounts.ProviderProfile", on_delete=models.CASCADE, related_name="points"
    )
    free_points = models.PositiveIntegerField(_("points offerts restants"), default=_welcome_points)
    points_due = models.PositiveIntegerField(_("points à payer"), default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("compte de points")
        verbose_name_plural = _("comptes de points")

    def __str__(self):
        return f"Points · {self.provider}"

    @property
    def blocked(self):
        return self.points_due >= settings.POINTS_BLOCK_AT

    @property
    def amount_due_da(self):
        return self.points_due * settings.POINT_VALUE_DA


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("À vérifier")
        APPROVED = "approved", _("Validé")
        REJECTED = "rejected", _("Refusé")

    account = models.ForeignKey(PointsAccount, on_delete=models.CASCADE, related_name="payments")
    points = models.PositiveIntegerField(_("points réglés"))
    amount_da = models.PositiveIntegerField(_("montant (DA)"))
    reference = models.CharField(_("référence BaridiMob"), max_length=80, blank=True)
    screenshot = models.ImageField(_("capture BaridiMob"), upload_to="payments/%Y/%m/")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    admin_note = models.CharField(_("note (visible par le bricoleur)"), max_length=255, blank=True)
    created_at = models.DateTimeField(_("envoyé le"), auto_now_add=True)
    reviewed_at = models.DateTimeField(_("vérifié le"), null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = _("paiement BaridiMob")
        verbose_name_plural = _("paiements BaridiMob")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.amount_da} DA · {self.account.provider} ({self.get_status_display()})"


class PointEntry(models.Model):
    """Historique : chaque débit (contact) ou crédit (paiement, geste de l'admin)."""

    class Kind(models.TextChoices):
        CONTACT = "contact", _("Contact client")
        PAYMENT = "payment", _("Paiement validé")
        ADJUSTMENT = "adjustment", _("Ajustement administrateur")

    account = models.ForeignKey(PointsAccount, on_delete=models.CASCADE, related_name="entries")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    free_used = models.PositiveIntegerField(_("points offerts utilisés"), default=0)
    due_delta = models.IntegerField(_("variation des points à payer"), default=0)
    mission = models.ForeignKey(
        "marketplace.Mission", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("mouvement de points")
        verbose_name_plural = _("mouvements de points")
        ordering = ("-created_at", "-id")
        constraints = [
            # un seul débit par mission
            models.UniqueConstraint(
                fields=["mission"], condition=models.Q(kind="contact"), name="uniq_debit_par_mission"
            ),
        ]
