"""Rutas de la API REST. Se montan bajo ``/api/`` en ematel_site/urls.py."""

from django.urls import path

from .api_views import MeView, clientes, consumption_series, my_consumption, panel

urlpatterns = [
    path("me/", MeView.as_view(), name="api_me"),
    path("c_series/", consumption_series, name="api_c_series"),
    path("consumption/", my_consumption, name="api_my_consumption"),
    path("panel/", panel, name="api_panel"),
    path("clientes/", clientes, name="api_clientes"),
]
