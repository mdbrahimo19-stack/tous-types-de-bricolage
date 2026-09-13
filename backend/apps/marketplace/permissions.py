from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsRequestOwner(BasePermission):
    """L'objet appartient au client qui a créé la demande."""

    message = "Vous n'êtes pas le propriétaire de cette demande."

    def has_object_permission(self, request, view, obj):
        client_id = getattr(obj, "client_id", None) or getattr(getattr(obj, "request", None), "client_id", None)
        return client_id == request.user.id


class IsVerifiedProvider(BasePermission):
    """Prestataire avec téléphone vérifié et profil validé (règle AUT-06 + validation modérateur)."""

    message = "Réservé aux prestataires vérifiés."

    def has_permission(self, request, view):
        user = request.user
        if not (user.is_authenticated and user.is_provider and user.phone_verified):
            return False
        profile = getattr(user, "provider_profile", None)
        return profile is not None and profile.is_verified
