# accounts/api_url.py
"""Rutas de la API agrupadas, por si se quieren montar bajo un prefijo.

Este archivo importaba ``MyConsumptionListCreate`` y ``MyConsumptionDetail``,
que nunca existieron en api_views.py: incluirlo desde urls.py reventaba con
ImportError. Ahora solo referencia vistas reales.

Las rutas de la API estan declaradas directamente en ``ematel_site/urls.py``.
Para usar este modulo en su lugar:

    path("api/", include("accounts.api_url")),
"""

from django.urls import path

from .api_views import MeView, consumption_series, my_consumption

urlpatterns = [
    path("me/", MeView.as_view(), name="api_me"),
    path("c_series/", consumption_series, name="api_c_series"),
    path("consumption/", my_consumption, name="api_my_consumption"),
]
