from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """Arbre à 2 niveaux : une racine (parent=None) ou une prestation (parent=racine)."""

    class Unit(models.TextChoices):
        FLAT = "forfait", _("Forfait")
        HOUR = "heure", _("Heure")
        SQM = "m2", _("m²")
        DAY = "jour", _("Jour")

    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children",
        verbose_name=_("catégorie parente"),
    )
    name_fr = models.CharField(_("libellé (FR)"), max_length=120)
    name_ar = models.CharField(_("libellé (AR)"), max_length=120, blank=True)
    slug = models.SlugField(_("slug"), max_length=140, unique=True, blank=True)
    icon = models.CharField(_("icône"), max_length=60, blank=True)
    description_fr = models.TextField(_("description (FR)"), blank=True)
    description_ar = models.TextField(_("description (AR)"), blank=True)
    unit = models.CharField(_("unité de facturation"), max_length=10, choices=Unit.choices, default=Unit.FLAT)
    price_min = models.DecimalField(_("prix indicatif min (DA)"), max_digits=10, decimal_places=2, null=True, blank=True)
    price_max = models.DecimalField(_("prix indicatif max (DA)"), max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(_("actif"), default=True)
    order = models.PositiveSmallIntegerField(_("ordre d'affichage"), default=0)

    class Meta:
        verbose_name = _("catégorie")
        verbose_name_plural = _("catégories")
        ordering = ("order", "name_fr")

    def __str__(self):
        return self.name_fr if self.parent is None else f"{self.parent.name_fr} › {self.name_fr}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name_fr) or "categorie"
            slug, i = base, 2
            while Category.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_root(self):
        return self.parent_id is None


class ProviderCategory(models.Model):
    provider = models.ForeignKey(
        "accounts.ProviderProfile", on_delete=models.CASCADE, related_name="categories"
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="providers")
    years_experience = models.PositiveSmallIntegerField(_("années d'expérience"), default=0)
    hourly_rate = models.DecimalField(_("taux horaire (DA)"), max_digits=10, decimal_places=2, null=True, blank=True)
    flat_rate = models.DecimalField(_("forfait (DA)"), max_digits=10, decimal_places=2, null=True, blank=True)
    callout_fee = models.DecimalField(
        _("frais de déplacement (DA)"), max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = _("catégorie du prestataire")
        verbose_name_plural = _("catégories du prestataire")
        constraints = [
            models.UniqueConstraint(fields=["provider", "category"], name="uniq_provider_category"),
        ]

    def __str__(self):
        return f"{self.provider} · {self.category}"
