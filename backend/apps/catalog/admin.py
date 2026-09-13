from django.contrib import admin

from .models import Category, ProviderCategory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("__str__", "parent", "unit", "price_min", "price_max", "is_active", "order")
    list_filter = ("is_active", "parent", "unit")
    search_fields = ("name_fr", "name_ar", "slug")
    list_editable = ("order", "is_active")
    prepopulated_fields = {"slug": ("name_fr",)}


@admin.register(ProviderCategory)
class ProviderCategoryAdmin(admin.ModelAdmin):
    list_display = ("provider", "category", "years_experience", "hourly_rate", "flat_rate")
    search_fields = ("provider__user__phone", "provider__business_name", "category__name_fr")
    autocomplete_fields = ("provider", "category")
