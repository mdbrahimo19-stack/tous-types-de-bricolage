from rest_framework import serializers

from .models import Address, Commune, Wilaya


class WilayaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wilaya
        fields = ("id", "code", "name_fr", "name_ar", "is_active")


class CommuneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commune
        fields = ("id", "wilaya", "name_fr", "name_ar")


class AddressSerializer(serializers.ModelSerializer):
    wilaya_name = serializers.CharField(source="wilaya.name_fr", read_only=True)
    commune_name = serializers.CharField(source="commune.name_fr", read_only=True)

    class Meta:
        model = Address
        fields = (
            "id", "label", "wilaya", "wilaya_name", "commune", "commune_name",
            "quartier", "street", "latitude", "longitude", "notes", "is_default",
        )

    def validate(self, attrs):
        wilaya = attrs.get("wilaya") or getattr(self.instance, "wilaya", None)
        commune = attrs.get("commune") or getattr(self.instance, "commune", None)
        if wilaya and commune and commune.wilaya_id != wilaya.id:
            raise serializers.ValidationError({"commune": "La commune n'appartient pas à cette wilaya."})
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        address = super().create(validated_data)
        self._sync_default(address)
        return address

    def update(self, instance, validated_data):
        address = super().update(instance, validated_data)
        self._sync_default(address)
        return address

    def _sync_default(self, address):
        if address.is_default:
            Address.objects.filter(user=address.user).exclude(pk=address.pk).update(is_default=False)
