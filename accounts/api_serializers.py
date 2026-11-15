"""Serializadores de la API REST."""

from rest_framework import serializers

from .models import GasConsumption, Profile, User


class ProfileMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = (
            "location", "external_id", "manager_name", "phone", "address", "link",
            "last_maintenance", "next_maintenance",
            "report_frequency", "report_format", "report_email",
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
        read_only_fields = fields
