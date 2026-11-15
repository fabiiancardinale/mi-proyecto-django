"""Registro de modelos en el admin de Django (/admin/)."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import GasConsumption, Profile, User

PERFIL_FIELDSETS = (
    ("Sitio", {"fields": ("location", "external_id", "manager_name", "phone", "address", "link")}),
    ("Mantenciones", {"fields": ("last_maintenance", "next_maintenance", "maintenance_interval_months")}),
    ("Reportes", {"fields": ("report_frequency", "report_format", "report_email")}),
)


class ProfileInline(admin.StackedInline):
    model = Profile
    fk_name = "user"
    extra = 0
    fieldsets = PERFIL_FIELDSETS


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (("Rol", {"fields": ("role",)}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + ((None, {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email")
    inlines = [ProfileInline]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "location", "last_maintenance", "next_maintenance", "maintenance_interval_months")
    list_filter = ("next_maintenance", "maintenance_interval_months")
    search_fields = ("user__username", "external_id", "manager_name")
    fieldsets = ((None, {"fields": ("user",)}),) + PERFIL_FIELDSETS


@admin.register(GasConsumption)
class GasConsumptionAdmin(admin.ModelAdmin):
    list_display = ("user", "year", "month", "m3_water", "m3_gas", "cost")
    list_filter = ("year", "month")
    search_fields = ("user__username", "user__email")
    ordering = ("-year", "user__username")
