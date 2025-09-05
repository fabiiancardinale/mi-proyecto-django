# accounts/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import Profile

User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = True
    fk_name = "user"
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # Mostrar el campo "role" en el admin de usuarios
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Rol", {"fields": ("role",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (None, {"fields": ("role",)}),
    )

    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email")

    inlines = [ProfileInline]


# apps/tu_app/admin.py
from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "location",
        "last_maintenance",
        "next_maintenance",
        "maintenance_interval_months",
    )
    list_filter = ("next_maintenance", "maintenance_interval_months")
    search_fields = ("user__username", "external_id", "manager_name")
    fieldsets = (
        (None, {"fields": ("user",)}),
        ("Datos", {"fields": ("location", "external_id", "manager_name", "phone", "address", "link")}),
        ("Mantenciones", {"fields": ("last_maintenance", "next_maintenance", "maintenance_interval_months")}),
    )


# accounts/admin.py
from django.contrib import admin
from .models import GasConsumption

@admin.register(GasConsumption)
class GasConsumptionAdmin(admin.ModelAdmin):
    list_display = ("user", "year", "month", "m3_water", "m3_gas", "cost")
    list_filter = ("year", "month")
    search_fields = ("user__username", "user__email")
    ordering = ("-year", "-month")
