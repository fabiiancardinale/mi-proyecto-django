# accounts/management/commands/revisar_migracion.py
"""Inspecciona la base ANTES de migrar y reporta que va a cambiar.

Las migraciones 0011, 0012 y 0013 modifican y borran datos existentes. Este
comando no escribe nada: solo lee la base actual y muestra exactamente que
haria cada una, para poder decidir con informacion antes de ejecutarlas.

    python manage.py revisar_migracion
"""

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import connection

MESES_VALIDOS = {
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
}
ALIAS_MES = {
    "enero": "ene", "febrero": "feb", "marzo": "mar", "abril": "abr",
    "mayo": "may", "junio": "jun", "julio": "jul", "agosto": "ago",
    "septiembre": "sep", "setiembre": "sep", "sept": "sep",
    "octubre": "oct", "noviembre": "nov", "diciembre": "dic",
}


def abreviar(valor):
    base = (valor or "").strip().lower().split("-")[0].strip()
    if not base:
        return None
    if base in ALIAS_MES:
        return ALIAS_MES[base]
    return base[:3] if base[:3] in MESES_VALIDOS else None


class Command(BaseCommand):
    help = "Muestra que cambiarian las migraciones 0011-0013 sin aplicarlas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--detalle",
            action="store_true",
            help="Lista fila por fila en vez de solo los totales.",
        )

    def handle(self, *args, **opciones):
        detalle = opciones["detalle"]
        salida = self.stdout
        titulo = self.style.MIGRATE_HEADING
        alerta = self.style.WARNING
        error = self.style.ERROR
        bien = self.style.SUCCESS

        with connection.cursor() as cur:
            # ---------------------------------------------------------------
            salida.write(titulo("\n1. MIGRACION 0011 · normalizacion de meses y roles"))

            cur.execute("SELECT id, month FROM accounts_gasconsumption")
            filas_mes = cur.fetchall()

            cambian, ilegibles = [], []
            for fila_id, mes in filas_mes:
                nuevo = abreviar(mes)
                if nuevo is None:
                    ilegibles.append((fila_id, mes))
                elif nuevo != mes:
                    cambian.append((fila_id, mes, nuevo))

            salida.write(f"   Registros de consumo en total: {len(filas_mes)}")
            salida.write(f"   Meses que se reescribiran:     {len(cambian)}")
            if cambian:
                muestras = cambian if detalle else cambian[:8]
                for fila_id, antes, despues in muestras:
                    salida.write(f"      id={fila_id}: {antes!r} -> {despues!r}")
                if not detalle and len(cambian) > 8:
                    salida.write(f"      … y {len(cambian) - 8} mas (usa --detalle)")

            if ilegibles:
                salida.write(alerta(
                    f"   Meses que NO se reconocen ({len(ilegibles)}): se dejan intactos"
                ))
                for fila_id, mes in (ilegibles if detalle else ilegibles[:8]):
                    salida.write(alerta(f"      id={fila_id}: {mes!r}"))
            else:
                salida.write(bien("   Todos los meses son legibles"))

            # ---- Roles ----
            cur.execute("SELECT role, COUNT(*) FROM accounts_user GROUP BY role")
            roles = cur.fetchall()
            salida.write("\n   Roles actuales:")
            riesgo_rol = []
            for rol, cantidad in roles:
                destino = {"administrador": "admin", "admin": "admin",
                           "usuario": "user", "user": "user"}.get(
                    (rol or "").strip().lower())
                if destino is None:
                    riesgo_rol.append((rol, cantidad))
                    salida.write(error(
                        f"      {rol!r}: {cantidad} usuario(s) -> se forzara a 'user'"
                    ))
                elif destino != rol:
                    salida.write(f"      {rol!r}: {cantidad} -> {destino!r}")
                else:
                    salida.write(bien(f"      {rol!r}: {cantidad} (sin cambios)"))

            if riesgo_rol:
                salida.write(error(
                    "   ATENCION: esos usuarios perderan permisos de administrador.\n"
                    "   Si alguno debe seguir siendo admin, corrigelo a mano antes de migrar:\n"
                    "     UPDATE accounts_user SET role='admin' WHERE username='...';"
                ))

            # ---------------------------------------------------------------
            salida.write(titulo("\n2. MIGRACION 0012 · borrado de duplicados"))

            cur.execute(
                "SELECT id, user_id, year, month FROM accounts_gasconsumption "
                "ORDER BY id"
            )
            grupos = defaultdict(list)
            for fila_id, usuario, anio, mes in cur.fetchall():
                grupos[(usuario, anio, abreviar(mes) or mes)].append(fila_id)

            duplicados = {k: v for k, v in grupos.items() if len(v) > 1}
            a_borrar = sum(len(v) - 1 for v in duplicados.values())

            if not duplicados:
                salida.write(bien("   No hay duplicados. No se borrara ninguna fila."))
            else:
                salida.write(error(
                    f"   SE BORRARAN {a_borrar} fila(s) en {len(duplicados)} periodo(s)."
                ))
                salida.write("   Se conserva siempre la de id mas alto (la ultima escrita).")
                items = list(duplicados.items())
                for (usuario, anio, mes), ids in (items if detalle else items[:8]):
                    cur.execute(
                        "SELECT username FROM accounts_user WHERE id=%s", [usuario]
                    )
                    nombre = (cur.fetchone() or ["?"])[0]
                    conserva, borra = ids[-1], ids[:-1]
                    salida.write(
                        f"      {nombre} {mes} {anio}: conserva id={conserva}, "
                        f"borra {borra}"
                    )
                if not detalle and len(items) > 8:
                    salida.write(f"      … y {len(items) - 8} periodos mas (usa --detalle)")

            # ---------------------------------------------------------------
            salida.write(titulo("\n3. MIGRACION 0013 · cambios de esquema"))

            cur.execute(
                "SELECT COUNT(*) FROM accounts_gasconsumption WHERE year < 0"
            )
            anios_negativos = cur.fetchone()[0]
            if anios_negativos:
                salida.write(error(
                    f"   {anios_negativos} fila(s) con año negativo: la columna pasa a "
                    "UNSIGNED y la migracion FALLARA. Corrigelas primero."
                ))
            else:
                salida.write(bien("   Ningun año negativo: el cambio a UNSIGNED es seguro"))

            cur.execute(
                "SELECT COUNT(*) FROM accounts_profile WHERE CHAR_LENGTH(link) > 200"
                if connection.vendor == "mysql"
                else "SELECT COUNT(*) FROM accounts_profile WHERE LENGTH(link) > 200"
            )
            salida.write(bien(
                "   El campo link pasa de 200 a 500 caracteres (solo se amplia, "
                f"{cur.fetchone()[0]} link(s) ya superan 200)"
            ))

            salida.write(
                f"   La tabla de consumos tiene {len(filas_mes)} filas: el ALTER TABLE "
                "reconstruye la tabla y la bloquea mientras dura."
            )

            # ---------------------------------------------------------------
            salida.write(titulo("\n4. RESUMEN"))
            salida.write(f"   Filas de consumo que se modifican: {len(cambian)}")
            salida.write(f"   Filas de consumo que se BORRAN:    {a_borrar}")
            salida.write(f"   Usuarios con rol reescrito:        "
                         f"{sum(c for r, c in roles if (r or '').lower() not in ('admin', 'user'))}")

            if a_borrar or riesgo_rol or anios_negativos:
                salida.write(alerta(
                    "\n   Hay cambios destructivos. Haz respaldo antes:\n"
                    "     mysqldump -u USUARIO -p calderas_ematel > respaldo.sql"
                ))
            else:
                salida.write(bien("\n   Sin cambios destructivos. Aun asi, respalda."))
            salida.write("")
