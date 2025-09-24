# accounts/serializers.py
from rest_framework import serializers
from .models import User, Profile, GasConsumption

class ProfileMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = (
            "location", "external_id", "manager_name", "phone", "address", "link",
            "last_maintenance", "next_maintenance", "report_frequency",
            "report_format", "report_email",
        )

class MeSerializer(serializers.ModelSerializer):
    profile = ProfileMiniSerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role", "profile")

class GasConsumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GasConsumption
        fields = ("id", "user", "year", "month", "day", "m3_water", "m3_gas", "cost")
        extra_kwargs = {
            # El usuario final no debería setear 'user'; lo controla la vista,
            # pero a los admins sí les dejamos enviarlo (lo manejamos en perform_create).
            "user": {"required": False},
        }
