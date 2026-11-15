"""Crea usuarios y consumo de ejemplo para probar el panel en local.

Uso::

    python manage.py datos_demo

Crea (o reutiliza) estas cuentas, todas con la contraseña ``demo1234``:

* ``admin``    → administrador
* ``hotel``    → cliente con link de Wecon y dos años de consumo
* ``colegio``  → cliente sin link, con mantención vencida

Es idempotente: correrlo varias veces no duplica datos.
Se niega a correr si la base no es SQLite, para no tocar la base real.
"""

import datetime
import random
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts import months
from accounts.models import Profile, User
from accounts.services import registrar_consumo

CLAVE = "demo1234"

CLIENTES = [
    {
        "username": "hotel",
        "email": "mantencion@hotelcentral.cl",
        "perfil": {
            "location": "Hotel Central · Santiago",
            "external_id": "WC-0142",
            "manager_name": "Carolina Muñoz",
            "phone": "+56 9 8765 4321",
            "address": "Av. Providencia 1234",
            "link": "https://example.com/wecon/hotel-central",
            "last_maintenance": -200,  # dias desde hoy
        },
        "base": (38, 120),  # (agua, gas) promedio mensual
    },
    {
        "username": "colegio",
        "email": "administracion@colegio.cl",
        "perfil": {
            "location": "Colegio San Andrés · Ñuñoa",
            "external_id": "WC-0087",
            "manager_name": "Jorge Pérez",
            "phone": "+56 2 2345 6789",
            "address": "Irarrázaval 3050",
            "link": "",
            "last_maintenance": -380,
        },
        "base": (22, 75),
    },
]


class Command(BaseCommand):
    help = "Crea usuarios y consumo de ejemplo (solo para desarrollo)."

    def handle(self, *args, **opciones):
        if not settings.DEBUG:
            raise CommandError("Solo se puede usar con DJANGO_DEBUG=True.")
        motor = settings.DATABASES["default"]["ENGINE"]
        if not motor.endswith("sqlite3"):
            raise CommandError(
                "Solo funciona con la base local SQLite (DJANGO_USAR_SQLITE=True). "
                "Así nunca se cargan usuarios de prueba en la base real."
            )

        random.seed(7)
        hoy = timezone.localdate()

        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@ematel.cl", "role": User.Roles.ADMIN},
        )
        admin.role = User.Roles.ADMIN
        admin.set_password(CLAVE)
        admin.save()

        for datos in CLIENTES:
            usuario, _ = User.objects.get_or_create(
                username=datos["username"], defaults={"email": datos["email"]}
            )
            usuario.set_password(CLAVE)
            usuario.save()

            perfil, _ = Profile.objects.get_or_create(user=usuario)
            campos = dict(datos["perfil"])
            perfil.last_maintenance = hoy + datetime.timedelta(days=campos.pop("last_maintenance"))
            perfil.next_maintenance = None  # se recalcula al guardar
            for campo, valor in campos.items():
                setattr(perfil, campo, valor)
            perfil.save()

            agua_base, gas_base = datos["base"]
            for anio in (hoy.year - 1, hoy.year):
                ultimo_mes = 12 if anio < hoy.year else hoy.month
                for numero in range(1, ultimo_mes + 1):
                    # Mas gas en invierno (junio-agosto en Chile).
                    invierno = 1.6 if numero in (6, 7, 8) else 1.25 if numero in (5, 9) else 1
                    agua = agua_base * random.uniform(.85, 1.15)
                    gas = gas_base * invierno * random.uniform(.85, 1.15)
                    registrar_consumo(
                        user=usuario,
                        year=anio,
                        month=months.CHOICES[numero - 1][0],
                        m3_water=Decimal(f"{agua:.2f}"),
                        m3_gas=Decimal(f"{gas:.2f}"),
                        cost=Decimal(round(gas * 1450 + agua * 900)),
                    )

        self.stdout.write(self.style.SUCCESS(
            f"Listo. Entra con admin / {CLAVE} o hotel / {CLAVE}."
        ))
