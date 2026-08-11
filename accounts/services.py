# accounts/services.py
"""Logica de negocio del consumo, fuera de las vistas.

El alta de consumo estaba copiada en tres sitios (``admin_dashboard``,
``user_dashboard`` y ``admin_add_consumption``), cada uno con su propia
variante de ``filter(...).first()`` seguido de ``save()`` o ``create()``.
Ademas de ser triple mantenimiento, ese patron tiene una condicion de
carrera: dos envios simultaneos del mismo mes crean dos filas.

Aqui vive una sola implementacion basada en ``update_or_create``, respaldada
por la restriccion de unicidad de la migracion 0013.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Sum

from . import months
from .models import GasConsumption
from monitoring.models import Consumption


class MesInvalido(ValueError):
    """El mes recibido no se pudo interpretar."""


# ---------------------------------------------------------------------------
# Alta y actualizacion de consumo
# ---------------------------------------------------------------------------
def _a_decimal(valor) -> Decimal:
    """Convierte a Decimal tolerando None, "" y comas decimales."""
    if valor in (None, ""):
        return Decimal("0")
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def registrar_consumo(
    *,
    user,
    year: int,
    month,
    m3_water=None,
    m3_gas=None,
    cost=None,
    day=None,
) -> tuple[GasConsumption, bool]:
    """Crea o actualiza el consumo de un mes.

    Devuelve ``(registro, fue_creado)``.

    El mes se normaliza siempre a su abreviatura canonica, asi que da igual si
    llega como "Mayo", "may-24" o 5.

    Lanza :class:`MesInvalido` si el mes no se reconoce; antes el codigo
    asumia enero en silencio, lo que ensuciaba los datos sin avisar.
    """
    abreviatura = months.abreviar(month)
    if abreviatura is None:
        raise MesInvalido(f"No se reconoce el mes {month!r}.")

    registro, creado = GasConsumption.objects.update_or_create(
        user=user,
        year=int(year),
        month=abreviatura,
        defaults={
            "m3_water": _a_decimal(m3_water),
            "m3_gas": _a_decimal(m3_gas),
            "cost": _a_decimal(cost),
            # El dia se recogia en el formulario pero nunca se guardaba.
            "day": int(day) if day not in (None, "") else None,
        },
    )
    return registro, creado


# ---------------------------------------------------------------------------
# Series para graficos
# ---------------------------------------------------------------------------
def serie_anual(user_id: int, year: int) -> dict[str, list[float]]:
    """Consumo de agua y gas de un usuario, en 12 posiciones (enero..diciembre)."""
    agua = [0.0] * 12
    gas = [0.0] * 12

    filas = (
        GasConsumption.objects
        .filter(user_id=user_id, year=year)
        .values("month")
        .annotate(agua=Sum("m3_water"), gas=Sum("m3_gas"))
    )
    for fila in filas:
        posicion = months.a_posicion(fila["month"])
        if posicion is None:
            continue  # dato historico ilegible: se ignora en vez de caer en enero
        agua[posicion] = float(fila["agua"] or 0)
        gas[posicion] = float(fila["gas"] or 0)

    return {"water": agua, "gas": gas}


def _serie_global(year: int) -> dict[str, list[float]]:
    """Consumo agregado de todas las calderas, desde la tabla legacy."""
    agua = [0.0] * 12
    gas = [0.0] * 12

    filas = (
        Consumption.objects
        .filter(date__year=year)
        .values("date__month")
        .annotate(agua=Sum("water_m3"), gas=Sum("gas_m3"))
    )
    for fila in filas:
        posicion = fila["date__month"] - 1
        if 0 <= posicion < 12:
            agua[posicion] = float(fila["agua"] or 0)
            gas[posicion] = float(fila["gas"] or 0)

    return {"water": agua, "gas": gas}


def datos_comparativa(*, user_id: int | None, anio_actual: int, anio_previo: int) -> dict:
    """Arma el payload que consumen los graficos de Chart.js.

    Si ``user_id`` viene, usa el consumo de ese usuario. Si no, el global.
    """
    if user_id:
        previo = serie_anual(user_id, anio_previo)
        actual = serie_anual(user_id, anio_actual)
    else:
        previo = _serie_global(anio_previo)
        actual = _serie_global(anio_actual)

    return {
        "labels": list(months.ETIQUETAS_CORTAS),
        "years": {"prev": anio_previo, "now": anio_actual},
        "water": {"prev": previo["water"], "now": actual["water"]},
        "gas": {"prev": previo["gas"], "now": actual["gas"]},
    }


# ---------------------------------------------------------------------------
# Historial y totales
# ---------------------------------------------------------------------------
@dataclass
class FilaHistorial:
    """Una fila de la tabla de historial, con su variacion interanual."""
    year: int
    month: str
    month_label: str
    m3_water: Decimal | None
    m3_gas: Decimal | None
    cost: Decimal | None
    diff_water: Decimal | None = None
    pct_water: float | None = None
    diff_gas: Decimal | None = None
    pct_gas: float | None = None


def _variacion(actual, anterior) -> tuple[Decimal | None, float | None]:
    """Diferencia absoluta y porcentual entre dos medidas."""
    if actual is None or anterior is None:
        return None, None
    diferencia = actual - anterior
    if not anterior:  # cubre 0 y Decimal("0"): evita division por cero
        return diferencia, None
    return diferencia, float(diferencia / anterior * 100)


def historial(user) -> list[FilaHistorial]:
    """Registros del usuario, del mas reciente al mas antiguo, con variacion
    contra el mismo mes del año anterior."""
    registros = list(
        GasConsumption.objects.filter(user=user).order_by("-year", "-id")
    )

    # Indice (año, mes) -> registro, para buscar el año anterior en O(1).
    indice = {}
    for registro in registros:
        abreviatura = months.abreviar(registro.month)
        if abreviatura:
            indice[(registro.year, abreviatura)] = registro

    filas = []
    for registro in registros:
        abreviatura = months.abreviar(registro.month)
        anterior = indice.get((registro.year - 1, abreviatura)) if abreviatura else None

        diff_agua, pct_agua = _variacion(
            registro.m3_water, anterior.m3_water if anterior else None
        )
        diff_gas, pct_gas = _variacion(
            registro.m3_gas, anterior.m3_gas if anterior else None
        )

        filas.append(FilaHistorial(
            year=registro.year,
            month=abreviatura or registro.month,
            month_label=months.etiqueta(registro.month, defecto=registro.month or "—"),
            m3_water=registro.m3_water,
            m3_gas=registro.m3_gas,
            cost=registro.cost,
            diff_water=diff_agua, pct_water=pct_agua,
            diff_gas=diff_gas, pct_gas=pct_gas,
        ))

    return filas


def resumen_anual(user, year: int | None) -> dict:
    """Totales y promedios de un año. Devuelve claves siempre presentes."""
    vacio = {
        "total_water": None, "total_gas": None, "total_cost": None,
        "water_avg": None, "gas_avg": None,
    }
    if not year:
        return vacio

    consulta = GasConsumption.objects.filter(user=user, year=year)
    return {
        **consulta.aggregate(
            total_water=Sum("m3_water"),
            total_gas=Sum("m3_gas"),
            total_cost=Sum("cost"),
        ),
        **consulta.aggregate(
            water_avg=Avg("m3_water"),
            gas_avg=Avg("m3_gas"),
        ),
    }


def buscar_mes(user, year: int | None, month) -> tuple[GasConsumption | None, dict | None]:
    """Busca el registro de un mes puntual y calcula su variacion interanual.

    Devuelve ``(registro, comparativa)``; ambos pueden ser ``None``.
    """
    abreviatura = months.abreviar(month)
    if not (year and abreviatura):
        return None, None

    actual = GasConsumption.objects.filter(
        user=user, year=year, month=abreviatura
    ).first()
    if actual is None:
        return None, None

    anterior = GasConsumption.objects.filter(
        user=user, year=year - 1, month=abreviatura
    ).first()
    if anterior is None:
        return actual, None

    diff_agua, pct_agua = _variacion(actual.m3_water, anterior.m3_water)
    diff_gas, pct_gas = _variacion(actual.m3_gas, anterior.m3_gas)

    return actual, {
        "prev_year": year - 1,
        "water_diff": diff_agua, "water_pct": pct_agua,
        "gas_diff": diff_gas, "gas_pct": pct_gas,
    }


def anios_disponibles(user) -> list[int]:
    """Años con registros, del mas reciente al mas antiguo.

    El ``order_by()`` vacio es obligatorio: el ``Meta.ordering`` del modelo
    incluye ``id``, y Django añade los campos de ordenamiento al SELECT, con
    lo que el DISTINCT dejaria de agrupar por año y devolveria repetidos.
    """
    return list(
        GasConsumption.objects.filter(user=user)
        .order_by()
        .values_list("year", flat=True)
        .distinct()
        .order_by("-year")
    )
