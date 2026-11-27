"""Droits des personnes (loi 18-07 modifiée par la loi 25-11) : accès (export) et effacement.

Effacement = ANONYMISATION : les missions, devis, avis et paiements restent (l'autre partie en a
besoin, et la comptabilité impose de garder les paiements), mais plus rien n'identifie la personne.
"""
from datetime import timedelta
from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.db.models.fields.files import FieldFile
from django.utils import timezone

ACTIVE_MISSION_STATUSES = ("planned", "confirmed", "in_progress")
OPEN_REQUEST_STATUSES = ("draft", "published", "quotes_received")
DELETED_NAME = "Utilisateur supprimé"


def _model(label):
    return apps.get_model(label)


def _value(v, request=None):
    if isinstance(v, FieldFile):
        if not v:
            return None
        return request.build_absolute_uri(v.url) if request else v.name
    if isinstance(v, Decimal):
        return str(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


def _rows(qs, request=None, exclude=()):
    """Tous les champs « simples » de chaque objet (clés étrangères = identifiants)."""
    out = []
    for obj in qs:
        row = {}
        for f in obj._meta.concrete_fields:
            if f.name in exclude:
                continue
            row[f.attname if f.is_relation else f.name] = _value(getattr(obj, f.attname), request)
        out.append(row)
    return out


def export_user_data(user, request=None):
    """Droit d'accès : tout ce que BRICOOL conserve sur cette personne, lisible et téléchargeable."""
    ServiceRequest = _model("marketplace.ServiceRequest")
    Quote = _model("marketplace.Quote")
    Mission = _model("marketplace.Mission")
    Message = _model("marketplace.Message")
    Review = _model("marketplace.Review")
    Notification = _model("marketplace.Notification")
    Address = _model("locations.Address")

    data = {
        "exporte_le": timezone.now().isoformat(),
        "compte": {
            "telephone": str(user.phone),
            "nom": user.full_name,
            "email": user.email,
            "langue": user.language,
            "photo": _value(user.photo, request),
            "client": user.is_client,
            "artisan": user.is_provider,
            "inscrit_le": _value(user.date_joined),
            "derniere_activite": _value(user.last_seen_at),
            "politique_confidentialite": {
                "version_acceptee": user.privacy_version,
                "acceptee_le": _value(user.privacy_accepted_at),
            },
        },
        "adresses": _rows(Address.objects.filter(user=user)),
        "demandes": _rows(ServiceRequest.objects.filter(client=user)),
        "devis_envoyes": _rows(Quote.objects.filter(provider=user)),
        "missions": _rows(Mission.objects.filter(Q(provider=user) | Q(request__client=user))),
        "messages_envoyes": _rows(Message.objects.filter(sender=user), request),
        "avis_ecrits": _rows(Review.objects.filter(author=user)),
        "avis_recus": _rows(Review.objects.filter(target=user)),
        "notifications": _rows(Notification.objects.filter(recipient=user)[:200]),
        "jours_de_visite": [
            {"jour": _value(v.day), "application": v.app or "autre"}
            for v in _model("accounts.DailyVisit").objects.filter(user=user)[:400]
        ],
    }
    profile = getattr(user, "provider_profile", None)
    if profile is not None:
        PointsAccount = _model("billing.PointsAccount")
        Payment = _model("billing.Payment")
        data["profil_artisan"] = _rows([profile], request, exclude=("verification_notes",))[0]
        data["profil_artisan"]["communes"] = list(profile.service_communes.values_list("name_fr", flat=True))
        data["realisations"] = _rows(profile.portfolio.all(), request)
        account = PointsAccount.objects.filter(provider=profile).first()
        if account:
            data["points"] = {"offerts_restants": account.free_points, "a_payer": account.points_due}
            data["paiements"] = _rows(Payment.objects.filter(account=account), request)
    return data


def deletion_blockers(user):
    """Raisons qui empêchent la suppression immédiate (liste vide = suppression possible)."""
    Mission = _model("marketplace.Mission")
    reasons = []
    active = Mission.objects.filter(
        Q(provider=user) | Q(request__client=user), status__in=ACTIVE_MISSION_STATUSES
    )
    if active.exists():
        reasons.append("Vous avez une mission en cours : terminez-la ou annulez-la d'abord.")
    profile = getattr(user, "provider_profile", None)
    if profile is not None:
        PointsAccount = _model("billing.PointsAccount")
        account = PointsAccount.objects.filter(provider=profile).first()
        if account and account.points_due > 0:
            reasons.append("Vous avez des points à payer : réglez-les d'abord (Mes points).")
    return reasons


def _placeholder_phone(user):
    # numéro factice unique (jamais attribué) : libère le vrai numéro sans casser l'unicité
    return f"+2130{user.pk:08d}"


@transaction.atomic
def anonymize_user(user):
    """Droit à l'effacement : efface tout ce qui identifie la personne et ferme le compte."""
    ServiceRequest = _model("marketplace.ServiceRequest")
    Notification = _model("marketplace.Notification")
    Address = _model("locations.Address")
    PhoneOTP = _model("accounts.PhoneOTP")
    DeviceToken = _model("accounts.DeviceToken")

    real_phone = user.phone
    # demandes encore ouvertes : annulées (les artisans ne les voient plus)
    ServiceRequest.objects.filter(client=user, status__in=OPEN_REQUEST_STATUSES).update(status="cancelled")
    Address.objects.filter(user=user).delete()
    Notification.objects.filter(recipient=user).delete()
    _model("accounts.DailyVisit").objects.filter(user=user).delete()
    DeviceToken.objects.filter(user=user).delete()
    PhoneOTP.objects.filter(phone=real_phone).delete()

    profile = getattr(user, "provider_profile", None)
    if profile is not None:
        for photo in profile.portfolio.all():
            photo.image.delete(save=False)
        profile.portfolio.all().delete()
        profile.service_communes.clear()
        profile.business_name = ""
        profile.bio = ""
        profile.rc_number = ""
        profile.nif = ""
        profile.latitude = None
        profile.longitude = None
        profile.is_available = False
        profile.save()

    if user.photo:
        user.photo.delete(save=False)
    user.photo = None
    user.full_name = DELETED_NAME
    user.email = ""
    user.phone = _placeholder_phone(user)
    user.is_active = False  # plus aucune connexion possible (les jetons sont refusés)
    user.set_unusable_password()
    user.save()
    return user


def purge(now=None, dry_run=False):
    """Nettoyage automatique (durées de la politique de confidentialité). Renvoie un résumé."""
    now = now or timezone.now()
    PhoneOTP = _model("accounts.PhoneOTP")
    Notification = _model("marketplace.Notification")
    User = _model("accounts.User")

    otps = PhoneOTP.objects.filter(created_at__lt=now - timedelta(days=1))
    notifications = Notification.objects.filter(created_at__lt=now - timedelta(days=180))
    # statistiques de fréquentation : gardées 13 mois (comparaison d'une année sur l'autre)
    _model("accounts.DailyVisit").objects.filter(day__lt=(now - timedelta(days=400)).date()).delete()
    limit = now - timedelta(days=365 * settings.PRIVACY_RETENTION_YEARS)
    inactive = (
        User.objects.filter(is_active=True, is_staff=False)
        .filter(Q(last_seen_at__lt=limit) | Q(last_seen_at__isnull=True, date_joined__lt=limit))
    )
    to_anonymize = [u for u in inactive if not deletion_blockers(u)]
    summary = {"codes_sms": otps.count(), "notifications": notifications.count(), "comptes_inactifs": len(to_anonymize)}
    if not dry_run:
        otps.delete()
        notifications.delete()
        for user in to_anonymize:
            anonymize_user(user)
    return summary
