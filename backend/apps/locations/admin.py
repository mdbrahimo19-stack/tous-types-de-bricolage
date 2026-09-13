from django.contrib import admin

from .models import Address, Commune, Wilaya


class CommuneInline(admin.TabularInline):
    model = Commune
    extra = 0


@admin.register(Wilaya)
class WilayaAdmin(admin.ModelAdmin):
    list_display = ("code", "name_fr", "name_ar", "is_active")
    list_filter = ("is_active",)
    list_editable = ("is_active",)
    search_fields = ("code", "name_fr", "name_ar")
    inlines = [CommuneInline]


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ("name_fr", "wilaya")
    list_filter = ("wilaya",)
    search_fields = ("name_fr", "name_ar")
    autocomplete_fields = ("wilaya",)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "commune", "wilaya", "is_default")
    list_filter = ("label", "wilaya")
    search_fields = ("user__phone", "user__full_name", "street", "quartier")
    autocomplete_fields = ("user", "wilaya", "commune")
