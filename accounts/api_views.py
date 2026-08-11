# accounts/api_views.py
"""API REST autenticada con JWT.

El mapa de meses y el armado de series vivian aqui duplicados respecto a
views.py, con reglas ligeramente distintas. Ahora ambos vienen de
``accounts.months`` y ``accounts.services``.
"""

from __future__ import annotations

from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import months, services
from .api_serializers import GasConsumptionSerializer, MeSerializer
from .models import GasConsumption


class MeView(APIView):
    """Datos de la cuenta y el perfil del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        datos = MeSerializer(request.user).data

        # El serializador no incluye campos calculados del perfil.
        perfil = getattr(request.user, "profile", None)
        if perfil is not None and datos.get("profile") is not None:
            datos["profile"]["days_to_next_maintenance"] = perfil.days_to_next_maintenance

        datos["last_login"] = (
            request.user.last_login.isoformat() if request.user.last_login else None
        )
        datos["date_joined"] = (
            request.user.date_joined.isoformat() if request.user.date_joined else None
        )
        datos["is_active"] = request.user.is_active
        return Response(datos)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def consumption_series(request):
    """Serie mensual de consumo del usuario autenticado.

    Devuelve doce posiciones (enero a diciembre); los meses sin dato van en 0.
    """
    try:
        year = int(request.GET.get("year", timezone.localdate().year))
    except (TypeError, ValueError):
        return Response({"detail": "Año inválido."}, status=400)

    serie = services.serie_anual(request.user.id, year)
    return Response({
        "year": year,
        "labels": list(months.NOMBRES),
        "water": serie["water"],
        "gas": serie["gas"],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_consumption(request):
    """Registros de consumo del usuario autenticado, opcionalmente por año."""
    registros = GasConsumption.objects.filter(user=request.user)

    year = request.GET.get("year")
    if year:
        try:
            registros = registros.filter(year=int(year))
        except (TypeError, ValueError):
            return Response({"detail": "Año inválido."}, status=400)

    return Response(GasConsumptionSerializer(registros, many=True).data)
