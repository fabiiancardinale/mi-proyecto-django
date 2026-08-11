# accounts/months.py
"""Fuente unica para el manejo de meses.

Antes esta informacion estaba repetida en cuatro sitios con variantes
distintas: ``MONTH_CHOICES`` en models.py y forms.py, ``MONTH_INDEX`` y
``MONTH_MAP`` en views.py, y otro ``MONTH_MAP`` mas amplio en api_views.py.
Cada copia aceptaba formatos ligeramente diferentes, que es justamente lo que
provocaba que ``GasConsumption.month`` terminara con valores mezclados
("may-24", "Mayo", "may").

Formato canonico de almacenamiento: abreviatura de tres letras en minuscula
("ene" .. "dic").
"""

from __future__ import annotations

import re

# Orden de enero a diciembre. El indice de la lista + 1 es el numero de mes.
ABREVIATURAS: tuple[str, ...] = (
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
)

NOMBRES: tuple[str, ...] = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)

# Etiquetas cortas para los ejes de los graficos.
ETIQUETAS_CORTAS: tuple[str, ...] = tuple(a.capitalize() for a in ABREVIATURAS)

# Para usar como ``choices`` en formularios: [("ene", "Enero"), ...]
CHOICES: list[tuple[str, str]] = list(zip(ABREVIATURAS, NOMBRES))

_INDICE_POR_ABREVIATURA: dict[str, int] = {a: i + 1 for i, a in enumerate(ABREVIATURAS)}
_ABREVIATURA_POR_NOMBRE: dict[str, str] = {
    n.lower(): a for n, a in zip(NOMBRES, ABREVIATURAS)
}

# Variantes que aparecen en datos historicos o que un usuario podria escribir.
_ALIAS: dict[str, str] = {
    "setiembre": "sep",
    "sept": "sep",
    "set": "sep",
    # Ingles, por si la API recibe datos de otro sistema.
    "jan": "ene", "apr": "abr", "aug": "ago", "dec": "dic",
    "january": "ene", "february": "feb", "march": "mar", "april": "abr",
    "june": "jun", "july": "jul", "august": "ago", "september": "sep",
    "october": "oct", "november": "nov", "december": "dic",
}

_SIN_TILDE = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")


def abreviar(valor: object) -> str | None:
    """Normaliza cualquier entrada razonable a "ene".."dic".

    Acepta:
      - entero 1..12
      - "5", "05"
      - "may", "Mayo", "MAYO", "mayo-24", "may-2024"
      - "september", "jan"

    Devuelve ``None`` si no se reconoce, para que quien llame decida que hacer
    en vez de asumir enero en silencio (que es lo que hacia el codigo viejo).
    """
    if valor is None or valor == "":
        return None

    # Enteros y booleanos (bool es subclase de int, lo excluimos).
    if isinstance(valor, int) and not isinstance(valor, bool):
        return ABREVIATURAS[valor - 1] if 1 <= valor <= 12 else None

    texto = str(valor).strip().lower().translate(_SIN_TILDE)
    if not texto:
        return None

    # Numero puro: "5", "05"
    if texto.isdigit():
        numero = int(texto)
        return ABREVIATURAS[numero - 1] if 1 <= numero <= 12 else None

    # Primer bloque alfabetico: cubre "may-24", "mayo 2024", "may/24"
    bloque = re.match(r"[a-z]+", texto)
    if bloque:
        palabra = bloque.group(0)
        if palabra in _ALIAS:
            return _ALIAS[palabra]
        if palabra in _ABREVIATURA_POR_NOMBRE:
            return _ABREVIATURA_POR_NOMBRE[palabra]
        if palabra[:3] in _INDICE_POR_ABREVIATURA:
            return palabra[:3]
        return None

    # Formatos numericos con separador: "2024-05", "05/2024"
    for numero in (int(n) for n in re.findall(r"\d{1,2}", texto)):
        if 1 <= numero <= 12:
            return ABREVIATURAS[numero - 1]

    return None


def a_indice(valor: object) -> int | None:
    """Devuelve 1..12, o ``None`` si el mes no se reconoce."""
    abreviatura = abreviar(valor)
    return _INDICE_POR_ABREVIATURA.get(abreviatura) if abreviatura else None


def a_posicion(valor: object) -> int | None:
    """Igual que :func:`a_indice` pero base 0, para indexar listas de 12."""
    indice = a_indice(valor)
    return indice - 1 if indice is not None else None


def etiqueta(valor: object, defecto: str = "—") -> str:
    """Nombre legible del mes: "may" -> "Mayo"."""
    indice = a_indice(valor)
    return NOMBRES[indice - 1] if indice else defecto


def es_valido(valor: object) -> bool:
    return abreviar(valor) is not None
