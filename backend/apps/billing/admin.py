from django.contrib import admin, messages
from django.utils.html import format_html

from . import services
from .models import Payment, PointEntry, PointsAccount


def _image(url, height):
    return format_html(
        '<a href="{0}" target="_blank"><img src="{0}" style="max-height:{1}px;border-radius:6px"></a>', url, height
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("created_at", "account", "method", "amount_da", "points", "reference", "status", "thumb")
    list_filter = ("status", "method")
    search_fields = ("reference", "checkout_id", "account__provider__user__phone", "account__provider__user__full_name",
                     "account__provider__business_name")
    readonly_fields = ("account", "method", "points", "amount_da", "reference", "checkout_id", "capture", "status",
                       "created_at", "reviewed_at", "reviewed_by")
    fields = ("account", "method", "amount_da", "points", "reference", "checkout_id", "capture", "status",
              "admin_note", "created_at", "reviewed_at", "reviewed_by")
    actions = ["approve", "reject"]
    date_hierarchy = "created_at"

    @admin.display(description="capture")
    def thumb(self, obj):
        return _image(obj.screenshot.url, 48) if obj.screenshot else "—"

    @admin.display(description="capture BaridiMob")
    def capture(self, obj):
        return _image(obj.screenshot.url, 520) if obj.screenshot else "—"

    def has_add_permission(self, request):
        return False  # seul le bricoleur envoie un paiement (depuis l'app)

    @admin.action(description="✅ Valider : argent reçu, débloquer le compte")
    def approve(self, request, queryset):
        n = 0
        for p in queryset.filter(status=Payment.Status.PENDING):
            services.approve_payment(p, by=request.user)
            n += 1
        self.message_user(request, f"{n} paiement(s) validé(s), compte(s) débloqué(s).", messages.SUCCESS)

    @admin.action(description="❌ Refuser : paiement non reçu")
    def reject(self, request, queryset):
        n = 0
        for p in queryset.filter(status=Payment.Status.PENDING):
            services.reject_payment(p, by=request.user)
            n += 1
        self.message_user(request, f"{n} paiement(s) refusé(s). Le bricoleur est prévenu.", messages.WARNING)


class PointEntryInline(admin.TabularInline):
    model = PointEntry
    extra = 0
    can_delete = False
    fields = ("created_at", "kind", "free_used", "due_delta", "note", "mission", "payment")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PointsAccount)
class PointsAccountAdmin(admin.ModelAdmin):
    list_display = ("provider", "free_points", "points_due", "amount", "is_blocked", "updated_at")
    search_fields = ("provider__user__phone", "provider__user__full_name", "provider__business_name")
    readonly_fields = ("provider", "updated_at")
    inlines = [PointEntryInline]

    @admin.display(description="à payer")
    def amount(self, obj):
        return f"{obj.amount_due_da:,} DA".replace(",", " ")

    @admin.display(description="bloqué", boolean=True)
    def is_blocked(self, obj):
        return obj.blocked

    def has_add_permission(self, request):
        return False  # créé automatiquement pour chaque bricoleur
