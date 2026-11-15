"""Rutas de la API REST. Se montan bajo ``/api/`` en ematel_site/urls.py."""

from django.urls import path

from . import api_admin
from .api_views import MeView, consumption_series, my_consumption, panel

urlpatterns = [
    path("me/", MeView.as_view(), name="api_me"),
    path("c_series/", consumption_series, name="api_c_series"),
    path("consumption/", my_consumption, name="api_my_consumption"),
    path("panel/", panel, name="api_panel"),
    path("admin/resumen/", api_admin.resumen, name="api_admin_resumen"),
    path("clientes/", api_admin.clientes, name="api_clientes"),
    path("clientes/<int:pk>/", api_admin.cliente, name="api_cliente"),
]
