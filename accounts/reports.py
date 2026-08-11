# accounts/reports.py
"""Generacion de reportes de consumo en CSV y PDF.

Estaba dentro de views.py mezclado con el manejo de peticiones. Ademas el
generador de PDF importaba reportlab dentro de la funcion y, si el paquete no
estaba instalado, el usuario recibia un 500 sin explicacion.
"""

from __future__ import annotations

import csv
import io

from django.utils.text import slugify

from . import months
from .models import GasConsumption

FORMATOS = {
    "csv": "text/csv",
    "pdf": "application/pdf",
}


class FormatoNoSoportado(ValueError):
    """Se pidio un formato distinto de csv o pdf."""


class ReportlabNoInstalado(RuntimeError):
    """Falta la dependencia para generar PDF."""


# ---------------------------------------------------------------------------
def filas_del_anio(user, year: int) -> list[list]:
    """Filas ordenadas cronologicamente: [año, mes, agua, gas, costo]."""
    registros = (
        GasConsumption.objects
        .filter(user=user, year=year)
        .values("year", "month", "m3_water", "m3_gas", "cost")
    )

    filas = [
        [
            r["year"],
            months.etiqueta(r["month"], defecto=r["month"] or "—"),
            float(r["m3_water"] or 0),
            float(r["m3_gas"] or 0),
            float(r["cost"] or 0),
            months.a_indice(r["month"]) or 13,  # clave de orden, se descarta luego
        ]
        for r in registros
    ]
    # Orden cronologico real. Antes se ordenaba por id, asi que el reporte
    # salia en el orden en que se cargaron los datos, no por mes.
    filas.sort(key=lambda f: f[5])
    return [f[:5] for f in filas]


def nombre_archivo(user, year: int, formato: str) -> str:
    return f"reporte-consumo-{slugify(user.username)}-{year}.{formato}"


# ---------------------------------------------------------------------------
def construir_csv(user, year: int) -> bytes:
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(["Usuario", user.username])
    escritor.writerow(["Año", year])
    escritor.writerow([])
    escritor.writerow(["AÑO", "MES", "M3_AGUA", "M3_GAS", "COSTO_CLP"])
    escritor.writerows(filas_del_anio(user, year))
    # BOM para que Excel en Windows respete los acentos.
    return buffer.getvalue().encode("utf-8-sig")


def construir_pdf(user, year: int) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover
        raise ReportlabNoInstalado(
            "Para generar reportes en PDF hace falta reportlab. "
            "Instalalo con: pip install -r requirements.txt"
        ) from exc

    buffer = io.BytesIO()
    lienzo = canvas.Canvas(buffer, pagesize=A4)
    ancho, alto = A4

    margen = 2 * cm
    filas = filas_del_anio(user, year)

    def cabecera(y: float) -> float:
        lienzo.setFont("Helvetica-Bold", 14)
        lienzo.drawString(margen, y, f"Reporte de consumo · {user.username} · {year}")
        y -= 1 * cm

        lienzo.setFont("Helvetica-Bold", 9)
        lienzo.drawString(margen, y, "AÑO")
        lienzo.drawString(margen + 1.6 * cm, y, "MES")
        lienzo.drawRightString(margen + 8 * cm, y, "AGUA (m³)")
        lienzo.drawRightString(margen + 11.5 * cm, y, "GAS (m³)")
        lienzo.drawRightString(margen + 15.5 * cm, y, "COSTO (CLP)")
        y -= 0.25 * cm
        lienzo.line(margen, y, ancho - margen, y)
        return y - 0.5 * cm

    y = cabecera(alto - margen)
    lienzo.setFont("Helvetica", 10)

    total_agua = total_gas = total_costo = 0.0
    for anio, mes, agua, gas, costo in filas:
        lienzo.drawString(margen, y, str(anio))
        lienzo.drawString(margen + 1.6 * cm, y, str(mes))
        lienzo.drawRightString(margen + 8 * cm, y, f"{agua:,.2f}")
        lienzo.drawRightString(margen + 11.5 * cm, y, f"{gas:,.2f}")
        lienzo.drawRightString(margen + 15.5 * cm, y, f"{costo:,.0f}")

        total_agua += agua
        total_gas += gas
        total_costo += costo

        y -= 0.55 * cm
        if y < margen + 2 * cm:
            lienzo.showPage()
            y = cabecera(alto - margen)
            lienzo.setFont("Helvetica", 10)

    if filas:
        y -= 0.2 * cm
        lienzo.line(margen, y, ancho - margen, y)
        y -= 0.6 * cm
        lienzo.setFont("Helvetica-Bold", 10)
        lienzo.drawString(margen, y, "TOTAL")
        lienzo.drawRightString(margen + 8 * cm, y, f"{total_agua:,.2f}")
        lienzo.drawRightString(margen + 11.5 * cm, y, f"{total_gas:,.2f}")
        lienzo.drawRightString(margen + 15.5 * cm, y, f"{total_costo:,.0f}")
    else:
        lienzo.setFont("Helvetica-Oblique", 10)
        lienzo.drawString(margen, y, "Sin registros de consumo para este año.")

    lienzo.showPage()
    lienzo.save()
    return buffer.getvalue()


def construir(user, year: int, formato: str) -> tuple[bytes, str, str]:
    """Devuelve ``(contenido, tipo_mime, nombre_archivo)``."""
    formato = (formato or "pdf").lower()
    if formato not in FORMATOS:
        raise FormatoNoSoportado(formato)

    contenido = construir_csv(user, year) if formato == "csv" else construir_pdf(user, year)
    return contenido, FORMATOS[formato], nombre_archivo(user, year, formato)
