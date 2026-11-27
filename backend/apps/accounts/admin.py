from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html

from .models import ClientProfile, DailyVisit, DeviceToken, PhoneOTP, PortfolioPhoto, ProviderProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("phone", "full_name", "is_client", "is_provider", "phone_verified", "is_active", "date_joined")
    list_filter = ("is_client", "is_provider", "phone_verified", "is_active", "is_staff")
    search_fields = ("phone", "full_name", "email")
    readonly_fields = ("date_joined", "last_login", "last_seen_at")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Identité", {"fields": ("full_name", "email", "photo", "language")}),
        ("Rôles", {"fields": ("is_client", "is_provider", "phone_verified")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("date_joined", "last_login", "last_seen_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone", "password1", "password2", "is_staff", "is_superuser")}),
    )


class PortfolioPhotoInline(admin.TabularInline):
    """Réalisations publiées par l'artisan : l'équipe peut retirer une photo inappropriée."""

    model = PortfolioPhoto
    extra = 0
    fields = ("preview", "image", "caption", "created_at")
    readonly_fields = ("preview", "created_at")

    @admin.display(description="Aperçu")
    def preview(self, obj):
        if not obj.image:
            return "—"
        return format_html('<img src="{}" style="height:80px;border-radius:8px">', obj.image.url)


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    inlines = (PortfolioPhotoInline,)
    list_display = ("user", "business_name", "legal_status", "verification_status", "rating_avg", "missions_count", "is_available")
    list_filter = ("verification_status", "legal_status", "is_available", "base_wilaya")
    search_fields = ("user__phone", "user__full_name", "business_name", "rc_number", "nif")
    autocomplete_fields = ("user", "base_wilaya")
    filter_horizontal = ("service_communes",)
    actions = ("approve_selected", "reject_selected")

    @admin.action(description="Valider les prestataires sélectionnés")
    def approve_selected(self, request, queryset):
        n = queryset.update(verification_status=ProviderProfile.Verification.APPROVED, verified_at=timezone.now())
        self.message_user(request, f"{n} prestataire(s) validé(s).")

    @admin.action(description="Refuser les prestataires sélectionnés")
    def reject_selected(self, request, queryset):
        n = queryset.update(verification_status=ProviderProfile.Verification.REJECTED)
        self.message_user(request, f"{n} prestataire(s) refusé(s).")


@admin.register(DailyVisit)
class DailyVisitAdmin(admin.ModelAdmin):
    """Fréquentation : une ligne par personne, par jour et par application (lecture seule)."""

    list_display = ("day", "user", "app")
    list_filter = ("app", "day")
    search_fields = ("user__phone", "user__full_name")
    date_hierarchy = "day"
    list_select_related = ("user",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "reliability_score", "created_at")
    search_fields = ("user__phone", "user__full_name")


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ("phone", "purpose", "created_at", "expires_at", "consumed_at", "attempts")
    list_filter = ("purpose",)
    search_fields = ("phone",)
    readonly_fields = ("code_hash",)


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "created_at", "last_used_at")
    search_fields = ("user__phone", "token")
