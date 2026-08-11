# accounts/management/commands/links_wecon.py
"""Exporta e importa en lote los links de equipos Wecon (Profile.link).

Pensado para la migracion de servidor de Wecon, donde cada equipo recibe una
URL nueva sin relacion con la anterior, asi que no sirve un reemplazo por
patron: hay que traer el listado completo.

Uso tipico
----------
1. Exportar la planilla con el estado actual::

       python manage.py links_wecon exportar --salida links.csv

2. Abrirla en Excel y rellenar la columna ``link_nuevo``.

3. Revisar que haria la importacion (no escribe nada)::

       python manage.py links_wecon importar --archivo links.csv

4. Aplicar los cambios de verdad::

       python manage.py links_wecon importar --archivo links.csv --aplicar
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Profile, User

COLUMNAS = [
    "usuario",
    "email",
    "ubicacion",
    "id_externo",
    "encargado",
    "link_actual",
    "link_nuevo",
]


class Command(BaseCommand):
    help = "Exporta o importa en lote los links de equipos Wecon."

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="accion", required=True)

        p_exp = sub.add_parser("exportar", help="Genera un CSV con los links actuales.")
        p_exp.add_argument(
            "--salida",
            default="links_wecon.csv",
            help="Ruta del CSV a generar (por defecto links_wecon.csv).",
        )
        p_exp.add_argument(
            "--solo-con-link",
            action="store_true",
            help="Exporta unicamente los usuarios que ya tienen un link configurado.",
        )

        p_imp = sub.add_parser("importar", help="Aplica los links de la columna link_nuevo.")
        p_imp.add_argument("--archivo", required=True, help="Ruta del CSV a leer.")
        p_imp.add_argument(
            "--aplicar",
            action="store_true",
            help="Escribe los cambios. Sin esta bandera solo muestra que haria.",
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **opciones):
        if opciones["accion"] == "exportar":
            return self._exportar(opciones)
        return self._importar(opciones)

    # ------------------------------------------------------------------
    def _exportar(self, opciones):
        destino = Path(opciones["salida"])

        perfiles = (
            Profile.objects.select_related("user")
            .order_by("user__username")
        )
        if opciones["solo_con_link"]:
            perfiles = perfiles.exclude(link="")

        with destino.open("w", newline="", encoding="utf-8-sig") as fh:
            escritor = csv.DictWriter(fh, fieldnames=COLUMNAS)
            escritor.writeheader()
            total = 0
            for perfil in perfiles:
                escritor.writerow({
                    "usuario": perfil.user.username,
                    "email": perfil.user.email or "",
                    "ubicacion": perfil.location or "",
                    "id_externo": perfil.external_id or "",
                    "encargado": perfil.manager_name or "",
                    "link_actual": perfil.link or "",
                    "link_nuevo": "",
                })
                total += 1

        self.stdout.write(self.style.SUCCESS(
            f"Exportados {total} usuarios a {destino.resolve()}"
        ))
        self.stdout.write(
            "Rellena la columna 'link_nuevo' y luego corre:\n"
            f"  python manage.py links_wecon importar --archivo {destino}"
        )

    # ------------------------------------------------------------------
    def _importar(self, opciones):
        origen = Path(opciones["archivo"])
        if not origen.exists():
            raise CommandError(f"No existe el archivo {origen}")

        aplicar = opciones["aplicar"]
        validar_url = URLValidator(schemes=["http", "https"])

        cambios, sin_cambio, errores = [], 0, []

        with origen.open(newline="", encoding="utf-8-sig") as fh:
            lector = csv.DictReader(fh)

            faltantes = {"usuario", "link_nuevo"} - set(lector.fieldnames or [])
            if faltantes:
                raise CommandError(
                    f"Al CSV le faltan columnas obligatorias: {', '.join(sorted(faltantes))}"
                )

            for nro, fila in enumerate(lector, start=2):  # 1 es la cabecera
                usuario = (fila.get("usuario") or "").strip()
                nuevo = (fila.get("link_nuevo") or "").strip()

                if not usuario:
                    errores.append(f"Fila {nro}: falta el nombre de usuario.")
                    continue
                if not nuevo:
                    continue  # fila sin link nuevo: se ignora en silencio

                try:
                    validar_url(nuevo)
                except ValidationError:
                    errores.append(f"Fila {nro} ({usuario}): '{nuevo}' no es una URL http/https valida.")
                    continue

                try:
                    perfil = Profile.objects.select_related("user").get(
                        user__username=usuario
                    )
                except Profile.DoesNotExist:
                    if User.objects.filter(username=usuario).exists():
                        errores.append(f"Fila {nro}: el usuario '{usuario}' no tiene perfil asociado.")
                    else:
                        errores.append(f"Fila {nro}: no existe el usuario '{usuario}'.")
                    continue

                if (perfil.link or "") == nuevo:
                    sin_cambio += 1
                    continue

                cambios.append((perfil, perfil.link or "(vacio)", nuevo))

        # ---- Informe ----
        self.stdout.write("")
        if cambios:
            titulo = "CAMBIOS A APLICAR" if aplicar else "SIMULACION (no se escribe nada)"
            self.stdout.write(self.style.MIGRATE_HEADING(titulo))
            for perfil, antes, despues in cambios:
                self.stdout.write(f"  {perfil.user.username}")
                self.stdout.write(self.style.WARNING(f"      antes:  {antes}"))
                self.stdout.write(self.style.SUCCESS(f"      ahora:  {despues}"))

        for problema in errores:
            self.stdout.write(self.style.ERROR(f"  ! {problema}"))

        self.stdout.write("")
        self.stdout.write(
            f"Resumen: {len(cambios)} por actualizar, "
            f"{sin_cambio} sin cambios, {len(errores)} con problemas."
        )

        if not aplicar:
            if cambios:
                self.stdout.write(self.style.WARNING(
                    "\nNada se guardo todavia. Repite el comando con --aplicar para escribir."
                ))
            return

        if errores:
            raise CommandError(
                "Hay filas con problemas. Corrige el CSV y vuelve a intentar; "
                "no se aplico ningun cambio."
            )

        with transaction.atomic():
            for perfil, _antes, despues in cambios:
                perfil.link = despues
                perfil.save(update_fields=["link"])

        self.stdout.write(self.style.SUCCESS(f"\nListo: {len(cambios)} links actualizados."))
