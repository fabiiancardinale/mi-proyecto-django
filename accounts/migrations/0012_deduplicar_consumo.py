# accounts/migrations/0012_deduplicar_consumo.py
"""Elimina consumos duplicados antes de imponer la restriccion de unicidad.

El codigo anterior hacia ``filter(...).first()`` y luego ``create()`` si no
encontraba nada. Con dos envios simultaneos del mismo mes ambos podian no
encontrar nada y crear dos filas. Tambien quedaron duplicados de cuando el
mes se guardaba con formatos distintos ("may" y "may-24" eran filas
diferentes para el mismo periodo).

Criterio: se conserva la fila con el ``id`` mas alto (la ultima escrita, que
es la que el usuario vio guardarse) y se descartan las demas.
"""

from collections import defaultdict

from django.db import migrations

MESES_VALIDOS = {
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
}


def _abreviar(valor):
    base = (valor or "").strip().lower().split("-")[0].strip()
    return base[:3] if base[:3] in MESES_VALIDOS else None


def deduplicar(apps, schema_editor):
    GasConsumption = apps.get_model("accounts", "GasConsumption")

    grupos = defaultdict(list)
    for registro in GasConsumption.objects.all().only("id", "user_id", "year", "month"):
        clave = (registro.user_id, registro.year, _abreviar(registro.month) or registro.month)
        grupos[clave].append(registro.id)

    a_borrar = []
    for ids in grupos.values():
        if len(ids) > 1:
            ids.sort()
            a_borrar.extend(ids[:-1])  # conserva el ultimo

    if a_borrar:
        GasConsumption.objects.filter(id__in=a_borrar).delete()


def revertir(apps, schema_editor):
    """Las filas duplicadas no se pueden recuperar; no hay marcha atras."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_normalizar_mes_y_rol"),
    ]

    operations = [
        migrations.RunPython(deduplicar, revertir),
    ]
