from django.contrib import admin

from .models import (
    AuditLog,
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


class RequestPhotoInline(admin.TabularInline):
    model = RequestPhoto
    extra = 0


class QuoteInline(admin.TabularInline):
    model = Quote
    extra = 0
    fields = ("provider", "amount", "lead_time_days", "status", "valid_until")
    readonly_fields = ("created_at",)


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "client", "commune", "urgency", "status", "published_at", "expires_at")
    list_filter = ("status", "urgency", "wilaya", "category")
    search_fields = ("title", "description", "client__phone", "client__full_name")
    autocomplete_fields = ("client", "category", "address", "wilaya", "commune")
    date_hierarchy = "created_at"
    inlines = [RequestPhotoInline, QuoteInline]


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "provider", "amount", "lead_time_days", "status", "valid_until", "created_at")
    list_filter = ("status",)
    search_fields = ("request__title", "provider__phone", "provider__full_name")
    autocomplete_fields = ("request", "provider")


class MissionPhotoInline(admin.TabularInline):
    model = MissionPhoto
    extra = 0


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "provider", "status", "scheduled_at", "amount_due", "paid_at")
    list_filter = ("status", "payment_method")
    search_fields = ("request__title", "provider__phone", "provider__full_name")
    autocomplete_fields = ("request", "quote", "provider")
    inlines = [MissionPhotoInline]


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("sender", "type", "body", "was_filtered", "flagged", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "client", "provider", "is_locked", "last_message_at")
    list_filter = ("is_locked",)
    search_fields = ("request__title", "client__phone", "provider__phone")
    autocomplete_fields = ("request", "client", "provider")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "type", "was_filtered", "flagged", "read_at", "created_at")
    list_filter = ("type", "flagged", "was_filtered")
    search_fields = ("body", "conversation__request__title", "sender__phone")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "target", "author", "rating", "moderation_status", "created_at")
    list_filter = ("rating", "moderation_status")
    search_fields = ("comment", "target__phone", "author__phone")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "type", "title", "channel", "is_read", "created_at")
    list_filter = ("type", "channel", "is_read")
    search_fields = ("title", "body", "recipient__phone")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target_type", "target_id", "ip")
    list_filter = ("action", "target_type")
    search_fields = ("action", "target_id", "actor__phone")
    readonly_fields = ("actor", "action", "target_type", "target_id", "changes", "ip", "created_at")

    def has_add_permission(self, request):
        return False
