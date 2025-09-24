# accounts/api_urls.py
from django.urls import path
from .api_views import MeView, MyConsumptionListCreate, MyConsumptionDetail

urlpatterns = [
    path("me/", MeView.as_view(), name="api_me"),

    # Consumos del usuario autenticado
    path("consumption/", MyConsumptionListCreate.as_view(), name="api_my_consumption_list_create"),
    path("consumption/<int:pk>/", MyConsumptionDetail.as_view(), name="api_my_consumption_detail"),
]
