from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import Address, Commune, Wilaya
from .serializers import AddressSerializer, CommuneSerializer, WilayaSerializer


class WilayaViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = WilayaSerializer
    queryset = Wilaya.objects.all().order_by("code")
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_active"]


class CommuneViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = CommuneSerializer
    queryset = Commune.objects.select_related("wilaya").order_by("name_fr")
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["wilaya"]


class AddressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return (
            Address.objects.filter(user=self.request.user)
            .select_related("wilaya", "commune")
            .order_by("-is_default", "-created_at")
        )
