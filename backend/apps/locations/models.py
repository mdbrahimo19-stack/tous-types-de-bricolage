from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Wilaya(models.Model):
    code = models.CharField(_("code"), max_length=3, unique=True)  # ex. "16" Alger
    name_fr = models.CharField(_("nom (FR)"), max_length=80)
    name_ar = models.CharField(_("nom (AR)"), max_length=80, blank=True)
    is_active = models.BooleanField(_("ouverte au service"), default=False)

    class Meta:
        verbose_name = _("wilaya")
        verbose_name_plural = _("wilayas")
        ordering = ("code",)

    def __str__(self):
        return f"{self.code} · {self.name_fr}"


class Commune(models.Model):
    wilaya = models.ForeignKey(Wilaya, on_delete=models.CASCADE, related_name="communes")
    name_fr = models.CharField(_("nom (FR)"), max_length=100)
    name_ar = models.CharField(_("nom (AR)"), max_length=100, blank=True)

    class Meta:
        verbose_name = _("commune")
        verbose_name_plural = _("communes")
        ordering = ("wilaya__code", "name_fr")
        constraints = [
            models.UniqueConstraint(fields=["wilaya", "name_fr"], name="uniq_commune_par_wilaya"),
        ]

    def __str__(self):
        return f"{self.name_fr} ({self.wilaya.code})"


class Address(models.Model):
    class Label(models.TextChoices):
        HOME = "domicile", _("Domicile")
        WORK = "travail", _("Travail")
        OTHER = "autre", _("Autre")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(_("libellé"), max_length=20, choices=Label.choices, default=Label.HOME)
    wilaya = models.ForeignKey(Wilaya, on_delete=models.PROTECT, related_name="+")
    commune = models.ForeignKey(Commune, on_delete=models.PROTECT, related_name="+")
    quartier = models.CharField(_("quartier"), max_length=120, blank=True)
    street = models.CharField(_("rue / n°"), max_length=200, blank=True)
    latitude = models.DecimalField(_("latitude"), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(_("longitude"), max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.CharField(_("indications d'accès"), max_length=255, blank=True)
    is_default = models.BooleanField(_("adresse par défaut"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("adresse")
        verbose_name_plural = _("adresses")
        ordering = ("-is_default", "-created_at")

    def __str__(self):
        return f"{self.get_label_display()} · {self.commune}"
