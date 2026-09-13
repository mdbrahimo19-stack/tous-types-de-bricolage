from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import Category
from .serializers import CategorySerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Catalogue public. `list` = familles racines (avec leurs prestations imbriquées)."""

    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        qs = Category.objects.filter(is_active=True).prefetch_related("children")
        if self.action == "list":
            qs = qs.filter(parent__isnull=True)
        return qs.order_by("order", "name_fr")
