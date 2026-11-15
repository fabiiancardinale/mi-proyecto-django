from django.contrib import admin

from .models import Consumption


@admin.register(Consumption)
class ConsumptionAdmin(admin.ModelAdmin):
    list_display = ("date", "boiler", "water_m3", "gas_m3")
    list_filter = ("boiler",)
    date_hierarchy = "date"
