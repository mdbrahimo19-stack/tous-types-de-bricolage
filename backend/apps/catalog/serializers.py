from rest_framework import serializers

from .models import Category


class CategoryBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name_fr", "name_ar", "slug", "icon", "unit", "price_min", "price_max")


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            "id", "name_fr", "name_ar", "slug", "icon",
            "description_fr", "description_ar", "unit", "price_min", "price_max", "children",
        )

    def get_children(self, obj):
        kids = [c for c in obj.children.all() if c.is_active]
        kids.sort(key=lambda c: (c.order, c.name_fr))
        return CategoryBriefSerializer(kids, many=True).data
