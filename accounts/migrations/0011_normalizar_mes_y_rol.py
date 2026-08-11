# accounts/migrations/0011_normalizar_mes_y_rol.py
"""Normaliza datos historicos de una sola vez.

Dos arrastres de versiones anteriores:

1. ``GasConsumption.month`` se guardo con formatos mezclados ("may-24",
   "Mayo", "may"). Esto se venia corrigiendo con un bucle a nivel de modulo
   en views.py que se ejecutaba en cada import. Aqui se hace una sola vez.

2. ``User.role`` guardo las etiquetas ("Administrador"/"Usuario") entre las
   migraciones 0002 y 0005, cuando los valores pasaron a ser "admin"/"user".
   La 0005 cambio los choices pero nunca migro las filas existentes, asi que
   en produccion conviven ambos formatos.
"""

from django.db import migrations

MESES_VALIDOS = {
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
}

# Formas largas y variantes que pueden existir en la base.
ALIAS_MES = {
    "enero": "ene", "febrero": "feb", "marzo": "mar", "abril": "abr",
    "mayo": "may", "junio": "jun", "julio": "jul", "agosto": "ago",
    "septiembre": "sep", "setiembre": "sep", "sept": "sep",
    "octubre": "oct", "noviembre": "nov", "diciembre": "dic",
}

ALIAS_ROL = {
    "administrador": "admin",
    "admin": "admin",
    "usuario": "user",
    "user": "user",
}


def _abreviar_mes(valor):
    """'May-24' -> 'may'. Devuelve None si no se reconoce."""
    base = (valor or "").strip().lower().split("-")[0].strip()
    if not base:
        return None
    if base in ALIAS_MES:
        return ALIAS_MES[base]
    corto = base[:3]
    return corto if corto in MESES_VALIDOS else None


def normalizar(apps, schema_editor):
    GasConsumption = apps.get_model("accounts", "GasConsumption")
    User = apps.get_model("accounts", "User")

    # --- Meses ---
    por_actualizar = []
    for registro in GasConsumption.objects.all().only("id", "month").iterator():
        nuevo = _abreviar_mes(registro.month)
        # Si no se reconoce el mes se deja intacto en vez de corromperlo:
        # es preferible un dato raro visible que uno silenciosamente erroneo.
        if nuevo and nuevo != registro.month:
            registro.month = nuevo
            por_actualizar.append(registro)

    if por_actualizar:
        GasConsumption.objects.bulk_update(por_actualizar, ["month"], batch_size=500)

    # --- Roles ---
    for antiguo, nuevo in (("Administrador", "admin"), ("Usuario", "user")):
        User.objects.filter(role=antiguo).update(role=nuevo)

    # Cualquier variante de mayusculas/minusculas que se haya colado.
    for usuario in User.objects.exclude(role__in=["admin", "user"]).only("id", "role"):
        destino = ALIAS_ROL.get((usuario.role or "").strip().lower())
        User.objects.filter(pk=usuario.pk).update(role=destino or "user")


def revertir(apps, schema_editor):
    """No hay vuelta atras significativa: los datos originales eran inconsistentes."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_profile_report_email_profile_report_format_and_more"),
    ]

    operations = [
        migrations.RunPython(normalizar, revertir),
    ]
