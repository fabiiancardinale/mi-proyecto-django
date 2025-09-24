# accounts/api_views.py
from __future__ import annotations

import re
from datetime import datetime

from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import ExtractMonth
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

# ===== Modelo de consumo =====
# Si tu modelo se llama GasConsumption (como en tus vistas), lo aliasamos como Consumption.
# Si en tu proyecto el modelo se llama Consumption, este try/except lo cubre.
try:
    from .models import GasConsumption as Consumption
except Exception:  # pragma: no cover
    from .models import Consumption  # type: ignore

User = get_user_model()

# ===== Utilidades de meses =====
MONTHS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

# Mapas amplio ES/EN
MONTH_MAP = {
    # ES corto
    "ene":1, "feb":2, "mar":3, "abr":4, "may":5, "jun":6,
    "jul":7, "ago":8, "sep":9, "oct":10, "nov":11, "dic":12,
    "set":9,  # a veces escriben 'setiembre'

    # ES largo
    "enero":1, "febrero":2, "marzo":3, "abril":4, "mayo":5, "junio":6,
    "julio":7, "agosto":8, "septiembre":9, "setiembre":9, "octubre":10,
    "noviembre":11, "diciembre":12,

    # EN corto
    "jan":1, "feb":2, "mar":3, "apr":4, "may":5, "jun":6,
    "jul":7, "aug":8, "sep":9, "oct":10, "nov":11, "dec":12,

    # EN largo
    "january":1, "february":2, "march":3, "april":4, "may":5, "june":6,
    "july":7, "august":8, "september":9, "october":10, "november":11, "december":12,
}

def _norm(s: str) -> str:
    return (s.lower()
              .replace("á","a").replace("é","e").replace("í","i")
              .replace("ó","o").replace("ú","u")
              .strip())

def month_to_index(m) -> int | None:
    """
    Acepta:
      - int: 1..12
      - '5' / '05'
      - 'may-24', 'jun-2025', 'Mar', 'Enero', 'jan', 'september'
      - '2025-05', '05-2025', '5/2025', etc.
    Devuelve 1..12 o None.
    """
    if m is None:
        return None
    if isinstance(m, int):
        return m if 1 <= m <= 12 else None

    s = _norm(str(m))

    # 1) ¿Solo número 1..12?
    if re.fullmatch(r"\d{1,2}", s):
        i = int(s)
        return i if 1 <= i <= 12 else None

    # 2) ¿hay token alfabético? (ej. 'may' en 'may-24')
    alpha = re.findall(r"[a-z]+", s)
    if alpha:
        tok = alpha[0]  # primer bloque alfabético
        if tok in MONTH_MAP:
            return MONTH_MAP[tok]
        # probar abreviado de 3 letras
        if len(tok) >= 3 and tok[:3] in MONTH_MAP:
            return MONTH_MAP[tok[:3]]

    # 3) ¿formato con números y separadores? (ej. '2025-05', '05-2025', '5/2025')
    nums = [int(n) for n in re.findall(r"\d{1,2}", s)]
    # intenta cada número como posible mes
    for n in nums:
        if 1 <= n <= 12:
            return n

    return None

# ===== /api/me/ =====
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        p = getattr(u, "profile", None)

        data = {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "role": getattr(u, "role", None),
            "is_active": u.is_active,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "date_joined": u.date_joined.isoformat() if u.date_joined else None,
            "profile": None,
        }

        if p:
            data["profile"] = {
                "location": p.location,
                "external_id": p.external_id,
                "manager_name": p.manager_name,
                "phone": p.phone,
                "address": p.address,
                "link": p.link,
                "last_maintenance": p.last_maintenance.isoformat() if p.last_maintenance else None,
                "next_maintenance": p.next_maintenance.isoformat() if p.next_maintenance else None,
                "maintenance_interval_months": p.maintenance_interval_months,
                "report_frequency": p.report_frequency,
                "report_format": p.report_format,
                "report_email": p.report_email,
                "days_to_next_maintenance": p.days_to_next_maintenance,
            }

        return Response(data)

# ===== /api/c_series/?year=YYYY =====
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def consumption_series(request):
    """
    Devuelve 12 posiciones (None si no hay dato):
    {
      "year": 2025,
      "labels": ["Enero",...,"Diciembre"],
      "water": [..12..],
      "gas":   [..12..]
    }
    """
    year = int(request.GET.get("year", timezone.now().year))
    water = [None] * 12
    gas   = [None] * 12

    # Campos del modelo (admite dos diseños):
    #  A) date (Date/DateTime)
    #  B) year:int + month:str/int
    field_names = {f.name for f in Consumption._meta.get_fields()}
    user_filter = {"user": request.user}  # FK a User con nombre 'user'

    if "date" in field_names:
        # A) Con campo fecha
        qs = (Consumption.objects
              .filter(**user_filter, date__year=year)
              .annotate(m=ExtractMonth("date"))
              .values("m")
              .annotate(w=Sum("m3_water"), g=Sum("m3_gas")))
        for row in qs:
            idx = int(row["m"]) - 1
            if 0 <= idx < 12:
                water[idx] = float(row["w"]) if row["w"] is not None else None
                gas[idx]   = float(row["g"]) if row["g"] is not None else None
    else:
        # B) Con year + month
        qs = (Consumption.objects
              .filter(**user_filter, year=year)
              .values("month")
              .annotate(w=Sum("m3_water"), g=Sum("m3_gas")))
        for row in qs:
            mi = month_to_index(row["month"])
            if mi:
                idx = mi - 1
                water[idx] = float(row["w"]) if row["w"] is not None else None
                gas[idx]   = float(row["g"]) if row["g"] is not None else None

    return Response({
        "year": year,
        "labels": MONTHS,
        "water": water,
        "gas": gas,
    })
