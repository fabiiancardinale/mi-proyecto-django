"""API REST autenticada con JWT. La consume la app Flutter (carpeta app_movil/).

Rutas (prefijo /api/):
  auth/token/      POST  usuario y contraseña -> tokens access y refresh
  auth/refresh/    POST  refresh -> nuevo access
  me/              GET   cuenta y perfil del usuario autenticado
  panel/           GET   todo lo que muestra el panel en una sola llamada
  consumption/     GET   registros; POST registra o actualiza un mes
  admin/..., clientes/...  administración (ver api_admin.py)
  c_series/        GET   serie mensual de un año

Un administrador puede consultar o registrar el consumo de otro usuario
pasando ``user_id`` (en la URL para GET, en el cuerpo para POST).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import months, services
from .api_admin import es_admin
from .api_serializers import GasConsumptionSerializer, MeSerializer
from .forms import AdminGasConsumptionForm, GasConsumptionForm
from .models import GasConsumption, User


def _es_admin(user) -> bool:
    return es_admin(user)


def _usuario_objetivo(request, user_id):
    """El propio usuario o, si es admin y lo pide, otro usuario."""
    if user_id in (None, "") or not _es_admin(request.user):
        return request.user
    return get_object_or_404(User, pk=user_id)


def _decimal_texto(valor):
    """Acepta "120,5" además de 120.5: en Chile se escribe con coma."""
    return valor.strip().replace(",", ".") if isinstance(valor, str) else valor


def _num(valor):
    """Decimal -> float para JSON; None se mantiene."""
    return float(valor) if valor is not None else None


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


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def my_consumption(request):
    """GET: registros del usuario (``?year=`` opcional).

    POST: registra o actualiza un mes. Cuerpo JSON::

        {"year": 2026, "month": "nov", "m3_water": 35.2, "m3_gas": 120}

    Solo se modifican los campos enviados con valor. ``cost`` y ``user_id``
    solo los acepta un administrador.
    """
    if request.method == "POST":
        return _registrar(request)

    usuario = _usuario_objetivo(request, request.GET.get("user_id"))
    registros = GasConsumption.objects.filter(user=usuario)
    year = request.GET.get("year")
    if year:
        try:
            registros = registros.filter(year=int(year))
        except (TypeError, ValueError):
            return Response({"detail": "Año inválido."}, status=400)
    return Response(GasConsumptionSerializer(registros, many=True).data)


def _registrar(request):
    datos = request.data
    admin = _es_admin(request.user)
    usuario = _usuario_objetivo(request, datos.get("user_id"))

    # Se reutilizan los formularios web: mismas reglas de validación.
    entrada = {
        "year": datos.get("year"),
        "month_choice": months.abreviar(datos.get("month")) or "",
        "day": datos.get("day"),
        "m3_water": _decimal_texto(datos.get("m3_water")),
        "m3_gas": _decimal_texto(datos.get("m3_gas")),
    }
    if admin:
        entrada.update(user=usuario.pk, cost=_decimal_texto(datos.get("cost")))
        formulario = AdminGasConsumptionForm(entrada)
    else:
        formulario = GasConsumptionForm(entrada)

    if not formulario.is_valid():
        errores = {campo: [str(e) for e in lista] for campo, lista in formulario.errors.items()}
        if "month_choice" in errores:
            errores["month"] = errores.pop("month_choice")
        return Response({"errores": errores}, status=400)

    limpio = formulario.cleaned_data
    registro, creado = services.registrar_consumo(
        user=usuario,
        year=limpio["year"],
        month=limpio["month_choice"],
        day=limpio.get("day"),
        m3_water=limpio.get("m3_water"),
        m3_gas=limpio.get("m3_gas"),
        cost=limpio.get("cost") if admin else None,
    )
    return Response(
        {"creado": creado, "registro": GasConsumptionSerializer(registro).data},
        status=201 if creado else 200,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def panel(request):
    """Todo lo que muestra el panel del cliente, en una sola respuesta."""
    usuario = _usuario_objetivo(request, request.GET.get("user_id"))
    perfil = getattr(usuario, "profile", None)

    historial = services.historial(usuario)
    anio = historial[0].year if historial else None
    resumen = services.resumen_anual(usuario, anio)

    return Response({
        "usuario": {
            "id": usuario.id,
            "username": usuario.username,
            "nombre": usuario.first_name or usuario.username,
            "email": usuario.email,
            "role": usuario.role,
            # Incluye superusuarios: es lo que decide si la app muestra la
            # vista de administrador.
            "es_admin": es_admin(usuario),
        },
        "perfil": {
            "location": perfil.location,
            "external_id": perfil.external_id,
            "manager_name": perfil.manager_name,
            "phone": perfil.phone,
            "address": perfil.address,
            "link": perfil.link,
            "last_maintenance": perfil.last_maintenance,
            "next_maintenance": perfil.next_maintenance,
            "days_to_next_maintenance": perfil.days_to_next_maintenance,
            "maintenance_interval_months": perfil.maintenance_interval_months,
        } if perfil else None,
        "anio": anio,
        "resumen": {clave: _num(valor) for clave, valor in resumen.items()},
        "series": {str(a): s for a, s in services.series_por_anio(usuario).items()},
        "historial": [
            {
                "year": f.year,
                "month": f.month,
                "month_label": f.month_label,
                "m3_water": _num(f.m3_water),
                "m3_gas": _num(f.m3_gas),
                "cost": _num(f.cost),
                "pct_water": f.pct_water,
                "pct_gas": f.pct_gas,
            }
            for f in historial
        ],
    })
