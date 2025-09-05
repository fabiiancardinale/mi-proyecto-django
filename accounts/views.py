# accounts/views.py
from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render, redirect
from django.utils import timezone
# imports (arriba):
from django.db.models import Sum, Avg

from .forms import AdminCreateUserForm, ProfileForm
from .models import User, Profile  # tu User custom
from monitoring.models import Consumption

# =============================
# Helpers de rol y auth
# =============================
def redirect_by_role(user):
    if getattr(user, "is_superuser", False):
        return "admin_dashboard"
    return "admin_dashboard" if user.is_admin() else "user_dashboard"


def role_required(*roles):
    roles_cf = {str(r).casefold() for r in roles}
    def deco(view_func):
        from functools import wraps
        @wraps(view_func)
        def _wrapped(request, *a, **kw):
            if not request.user.is_authenticated:
                return redirect("login")
            if getattr(request.user, "is_superuser", False):
                return view_func(request, *a, **kw)

            user_role_code = (getattr(request.user, "role", "") or "").casefold()
            # map código->etiqueta: {"admin":"Administrador", ...}
            label_by_code = dict(User.Roles.choices)
            user_role_label = (label_by_code.get(request.user.role, "") or "").casefold()

            if user_role_code not in roles_cf and user_role_label not in roles_cf:
                return redirect(redirect_by_role(request.user))
            return view_func(request, *a, **kw)
        return _wrapped
    return deco



admin_required = role_required("Administrador")
user_required  = role_required("Usuario", "Administrador")

# =============================
# Login / Logout / Home
# =============================
class LoginForm(forms.Form):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

def login_view(request):
    if request.user.is_authenticated:
        return redirect(redirect_by_role(request.user))
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        u = authenticate(request,
                         username=form.cleaned_data["username"],
                         password=form.cleaned_data["password"])
        if u:
            login(request, u)
            return redirect(redirect_by_role(u))
        form.add_error(None, "Credenciales inválidas.")
    return render(request, "login.html", {"form": form})

def home(request):
    if request.user.is_authenticated:
        return redirect(redirect_by_role(request.user))
    return render(request, "home.html")

def logout_view(request):
    logout(request)
    return redirect("login")

# =============================
# Dashboards
# =============================
# accounts/views.py
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.db.models.functions import TruncMonth
from django.db.models import Sum
from .models import User
from monitoring.models import Consumption
# accounts/views.py (añade/ajusta este bloque)

from django.http import JsonResponse
from django.contrib.auth import get_user_model

User = get_user_model()

# --- util: índice de mes para GasConsumption.month ---
MONTH_INDEX = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12
}
def _month_to_index(mstr: str) -> int:
    if not mstr:
        return 1
    key = mstr.strip().lower()[:3]
    return MONTH_INDEX.get(key, 1)

def build_chart_data(*, user_id: int | None, yr_now: int, yr_prev: int) -> dict:
    """
    Si user_id viene, usa GasConsumption por usuario (dos años).
    Si no, usa Consumption global (tu código actual).
    Retorna dict con labels, years, water(prev/now), gas(prev/now).
    """
    labels = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    agua_prev = [0.0]*12; agua_now = [0.0]*12
    gas_prev  = [0.0]*12; gas_now  = [0.0]*12

    if user_id:
        # ----- Por usuario: GasConsumption -----
        qs_prev = (GasConsumption.objects
                   .filter(user_id=user_id, year=yr_prev)
                   .values("month")
                   .annotate(w=Sum("m3_water"), g=Sum("m3_gas")))
        qs_now  = (GasConsumption.objects
                   .filter(user_id=user_id, year=yr_now)
                   .values("month")
                   .annotate(w=Sum("m3_water"), g=Sum("m3_gas")))
        for row in qs_prev:
            m_idx = _month_to_index(row["month"]) - 1
            agua_prev[m_idx] = float(row["w"] or 0)
            gas_prev[m_idx]  = float(row["g"] or 0)
        for row in qs_now:
            m_idx = _month_to_index(row["month"]) - 1
            agua_now[m_idx] = float(row["w"] or 0)
            gas_now[m_idx]  = float(row["g"] or 0)

    else:
        # ----- Global: Consumption (tu código original) -----
        qs = (
            Consumption.objects
            .filter(date__year__in=[yr_prev, yr_now])
            .annotate(m=TruncMonth('date'))
            .values('m', 'date__year')
            .annotate(water=Sum('water_m3'), gas=Sum('gas_m3'))
            .order_by('date__year', 'm')
        )
        for row in qs:
            m_idx = row['m'].month - 1
            if row['date__year'] == yr_prev:
                agua_prev[m_idx] = float(row['water'] or 0)
                gas_prev[m_idx]  = float(row['gas'] or 0)
            else:
                agua_now[m_idx] = float(row['water'] or 0)
                gas_now[m_idx]  = float(row['gas'] or 0)

    return {
        "labels": labels,
        "years": {"prev": yr_prev, "now": yr_now},
        "water": {"prev": agua_prev, "now": agua_now},
        "gas":   {"prev": gas_prev,  "now": gas_now},
    }
# accounts/views.py
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from django.contrib.auth import get_user_model
User = get_user_model()

from .forms import AdminGasConsumptionForm
from .models import GasConsumption
from monitoring.models import Consumption  # si tu build_chart_data usa Consumption global
from django.db.models.functions import TruncMonth

# Si no lo tienes en otro archivo, importa la util:
# from .utils import build_chart_data
# O pega aquí la firma de build_chart_data y su lógica.

@admin_required
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Dashboard de administrador con:
      - Form para agregar consumo (elige usuario, año/mes, agua/gas)
      - Tabla de consumo del usuario seleccionado (?selected_user=ID)
      - Gráficos (globales o del usuario seleccionado)
      - Listado/paginación/filtros de usuarios
    """
    # ==== Años para gráficos ====
    now = timezone.localdate()
    yr_now = now.year
    yr_prev = yr_now - 1

    # ==== Form Admin: Agregar Consumo ====
    admin_form = AdminGasConsumptionForm(request.POST or None)

    if request.method == "POST":
        if admin_form.is_valid():
            obj = admin_form.save()  # usa el usuario elegido en el propio form
            messages.success(
                request,
                f"Consumo guardado para {obj.user.username} ({obj.year}-{obj.month})."
            )
            # Redirige manteniendo el usuario seleccionado para ver su tabla y refrescar gráficos
            return redirect(f"{request.path}?selected_user={obj.user_id}")
        else:
            messages.error(request, "Revisa los datos del formulario.")

    # ==== Usuario seleccionado para tabla/gráfico ====
    selected_user_id = request.GET.get("selected_user")
    su = int(selected_user_id) if (selected_user_id and selected_user_id.isdigit()) else None

    # ==== Gráficos: por usuario si hay seleccionado; si no, global ====
    chart_data = build_chart_data(user_id=su, yr_now=yr_now, yr_prev=yr_prev)

    # ==== Tabla de consumo para el usuario seleccionado ====
    rows, totals, year_now_tbl = [], {}, None
    if su:
        qs = GasConsumption.objects.filter(user_id=su).order_by("-year", "-id")
        MONTH_MAP = {
            "ene": "Enero","feb":"Febrero","mar":"Marzo","abr":"Abril",
            "may":"Mayo","jun":"Junio","jul":"Julio","ago":"Agosto",
            "sep":"Septiembre","oct":"Octubre","nov":"Noviembre","dic":"Diciembre",
        }
        def _norm_month(m: str) -> str:
            return (m or "").strip().lower().split("-")[0][:3]
        for r in qs:
            rows.append({
                "year": r.year,
                "month_label": MONTH_MAP.get(_norm_month(r.month), r.month or "—"),
                "m3_water": r.m3_water,
                "m3_gas": r.m3_gas,
                "cost": r.cost,
            })
        year_now_tbl = qs.first().year if qs else None
        if year_now_tbl:
            totals = GasConsumption.objects.filter(user_id=su, year=year_now_tbl).aggregate(
                total_water=Sum("m3_water"),
                total_gas=Sum("m3_gas"),
                total_cost=Sum("cost"),
            )

    # ==== Combo de usuarios para selects en la UI ====
    users_for_filter = User.objects.order_by("username").only("id", "username")

    # ==== Lista + filtros/paginación de usuarios (lo tuyo de siempre) ====
    q = (request.GET.get("q") or "").strip()
    role = (request.GET.get("role") or "").strip()
    status = (request.GET.get("status") or "").strip()

    users = User.objects.all().order_by("id")
    if q:
        users = users.filter(Q(username__icontains=q) | Q(email__icontains=q))
    if role in ("Administrador", "Usuario"):
        users = users.filter(role__iexact=role)
    if status == "activos":
        users = users.filter(is_active=True)
    elif status == "inactivos":
        users = users.filter(is_active=False)

    paginator = Paginator(users, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # ==== Contexto ====
    context = {
        # Gráficos
        "chart_data": chart_data,

        # Form admin para agregar consumo
        "admin_form": admin_form,

        # Tabla del usuario seleccionado
        "selected_user_id": selected_user_id,
        "rows": rows,
        "year_now_tbl": year_now_tbl,
        "totals": totals,

        # Selects/tabla de usuarios
        "users_for_filter": users_for_filter,
        "page_obj": page_obj,
        "paginator": paginator,
        "q": q,
        "role_filter": role,
        "status_filter": status,
        "total_users": User.objects.count(),
        "total_activos": User.objects.filter(is_active=True).count(),
        "total_inactivos": User.objects.filter(is_active=False).count(),
    }
    return render(request, "admin_dashboard.html", context)

@admin_required
def admin_chart_data(request):
    """
    Endpoint AJAX: retorna chart_data para un user_id dado (o global si viene vacío).
    GET params: user_id (opcional), year_now (opcional), year_prev (opcional)
    """
    user_id = request.GET.get("user_id")
    user_id = int(user_id) if (user_id and user_id.isdigit()) else None

    now = timezone.localdate()
    yr_now = int(request.GET.get("year_now") or now.year)
    yr_prev = int(request.GET.get("year_prev") or (yr_now - 1))

    data = build_chart_data(user_id=user_id, yr_now=yr_now, yr_prev=yr_prev)
    return JsonResponse({"chart_data": data})



# accounts/views.py
from django.contrib.auth.decorators import login_required  # o tu @user_required
from django.db.models import Sum
from django.shortcuts import render

from .models import GasConsumption  # y tu Profile si lo manejas aparte

# Si usas tu propio decorador, deja @user_required. Aquí muestro login_required como referencia.
# accounts/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum

from .models import GasConsumption
from .forms import GasConsumptionForm  # asegúrate de tener este ModelForm (lo dejo abajo)
# accounts/views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import render, redirect
from .models import GasConsumption
from .forms import GasConsumptionForm

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum, Avg

@login_required
def user_dashboard(request):
    user = request.user
    profile = getattr(user, "profile", None)

    if request.method == "POST":
        form = GasConsumptionForm(request.POST)
        if form.is_valid():
            form.save(user=user)  # <-- pasa el usuario; el form arma month y setea user
            messages.success(request, "Consumo guardado correctamente.")
            return redirect("user_dashboard")
        else:
            messages.error(request, "Revisa los datos del formulario.")
    else:
        form = GasConsumptionForm()

    qs = GasConsumption.objects.filter(user=user).order_by("-year", "-id")

    MONTH_MAP = {
        "ene": "Enero","feb":"Febrero","mar":"Marzo","abr":"Abril",
        "may":"Mayo","jun":"Junio","jul":"Julio","ago":"Agosto",
        "sep":"Septiembre","oct":"Octubre","nov":"Noviembre","dic":"Diciembre",
    }
    def norm_month(mstr: str) -> str:
        return (mstr or "").strip().lower().split("-")[0][:3]
    def month_label(mstr: str) -> str:
        return MONTH_MAP.get(norm_month(mstr), mstr or "—")

    idx = {(r.year, norm_month(r.month)): r for r in qs}
    rows = []
    for r in qs:
        prev = idx.get((r.year - 1, norm_month(r.month)))
        diff_w = pct_w = diff_g = pct_g = None
        if prev and r.m3_water and prev.m3_water:
            diff_w = r.m3_water - prev.m3_water
            if prev.m3_water != 0:
                pct_w = (diff_w / prev.m3_water) * 100
        if prev and r.m3_gas and prev.m3_gas:
            diff_g = r.m3_gas - prev.m3_gas
            if prev.m3_gas != 0:
                pct_g = (diff_g / prev.m3_gas) * 100

        rows.append({
            "year": r.year,
            "month_label": month_label(r.month),
            "m3_water": r.m3_water,
            "m3_gas": r.m3_gas,
            "cost": r.cost,
            "diff_water": diff_w, "pct_water": pct_w,
            "diff_gas": diff_g, "pct_gas": pct_g,
        })

    year_now = qs.first().year if qs else None
    totals = {}
    avg_current = {"water_avg": None, "gas_avg": None}

    if year_now:
        totals = GasConsumption.objects.filter(user=user, year=year_now).aggregate(
            total_water=Sum("m3_water"),
            total_gas=Sum("m3_gas"),
            total_cost=Sum("cost"),
        )
        avgs = GasConsumption.objects.filter(user=user, year=year_now).aggregate(
            water_avg=Avg("m3_water"),
            gas_avg=Avg("m3_gas"),
        )
        avg_current["water_avg"] = avgs["water_avg"]
        avg_current["gas_avg"]   = avgs["gas_avg"]

    # ▼ NUEVO: soporte para el bloque “Buscar Consumo”
    # Listas para selects
    years_available = sorted({r.year for r in qs}, reverse=True)
    months_available = list(MONTH_MAP.values())
    LABEL_TO_ABBR = {v: k for k, v in MONTH_MAP.items()}

    # Parámetros seleccionados (GET)
    selected_year = None
    selected_month = (request.GET.get("month") or "").strip()
    _year_qs = request.GET.get("year")

    if _year_qs:
        try:
            selected_year = int(_year_qs)
        except (TypeError, ValueError):
            selected_year = year_now
    else:
        selected_year = year_now

    # Buscar registro puntual y calcular YoY
    current_entry = None
    yoy = None

    if selected_year and selected_month:
        abbr = LABEL_TO_ABBR.get(selected_month)
        if abbr:
            # Buscar el registro del mes/año seleccionado
            for r in qs:
                if r.year == selected_year and norm_month(r.month) == abbr:
                    current_entry = r
                    break

            # Si existe registro, armar YoY contra (año-1)
            if current_entry:
                prev = None
                for r in qs:
                    if r.year == (selected_year - 1) and norm_month(r.month) == abbr:
                        prev = r
                        break

                if prev:
                    water_diff = None
                    water_pct = None
                    gas_diff = None
                    gas_pct = None

                    if current_entry.m3_water is not None and prev.m3_water is not None:
                        water_diff = current_entry.m3_water - prev.m3_water
                        if prev.m3_water != 0:
                            water_pct = (water_diff / prev.m3_water) * 100

                    if current_entry.m3_gas is not None and prev.m3_gas is not None:
                        gas_diff = current_entry.m3_gas - prev.m3_gas
                        if prev.m3_gas != 0:
                            gas_pct = (gas_diff / prev.m3_gas) * 100

                    yoy = {
                        "prev_year": selected_year - 1,
                        "water_diff": water_diff,
                        "water_pct": water_pct,
                        "gas_diff": gas_diff,
                        "gas_pct": gas_pct,
                    }
    # ▲ NUEVO

    return render(request, "user_dashboard.html", {
        "profile": profile,
        "rows": rows,
        "year_now": year_now,
        "totals": totals,
        "avg_current": avg_current,   # <-- ya lo pasabas
        "form": form,

        # ▼ NUEVO en el contexto
        "years_available": years_available,
        "months_available": months_available,
        "selected_year": selected_year,
        "selected_month": selected_month,
        "current_entry": current_entry,
        "yoy": yoy,
        # ▲ NUEVO
    })


# =============================
# Crear usuario + perfil
# =============================
# accounts/views.py
from django.db import transaction, IntegrityError
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import AdminCreateUserForm, ProfileForm
from .models import Profile, User
from .views import admin_required  # o desde donde tengas el decorador

@admin_required
def create_user(request):
    if request.method == "POST":
        uform = AdminCreateUserForm(request.POST)
        pform = ProfileForm(request.POST)
        if uform.is_valid() and pform.is_valid():
            with transaction.atomic():
                user = uform.save(commit=False)
                user.role = uform.cleaned_data["role"]
                user.is_staff = False
                user.is_superuser = False
                user.save()

                profile, _ = Profile.objects.get_or_create(user=user)
                pform = ProfileForm(request.POST, instance=profile)
                pform.full_clean()
                pform.save()

            messages.success(request, f"Usuario '{user.username}' creado correctamente.")
            return redirect("admin_dashboard")
        messages.error(request, "Revisa los campos, hay errores en el formulario.")
    else:
        uform = AdminCreateUserForm()
        pform = ProfileForm()

    return render(request, "register_user.html", {"uform": uform, "pform": pform})



# accounts/views.py
import csv, io, datetime
from django.http import HttpResponse, JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.utils.text import slugify
from .models import GasConsumption

# -------- util para reunir datos por año --------
def _user_consumption_by_year(user, year:int):
    qs = (GasConsumption.objects
          .filter(user=user, year=year)
          .order_by("id")
          .values("year", "month", "m3_water", "m3_gas", "cost"))
    rows = []
    for r in qs:
        rows.append([
            r["year"], r["month"],
            float(r["m3_water"] or 0),
            float(r["m3_gas"] or 0),
            float(r["cost"] or 0),
        ])
    return rows

# -------- generar CSV (bytes) --------
def _build_csv(user, year:int) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Usuario", user.username])
    w.writerow(["Año", year])
    w.writerow([])
    w.writerow(["AÑO","MES","M3_AGUA","M3_GAS","COSTO_CLP"])
    for row in _user_consumption_by_year(user, year):
        w.writerow(row)
    return buf.getvalue().encode("utf-8")

# -------- generar PDF (bytes) con reportlab --------
def _build_pdf(user, year:int) -> bytes:
    # pip install reportlab
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, h-2*cm, f"Reporte de Consumo - {user.username} - {year}")

    c.setFont("Helvetica", 10)
    y = h-3*cm
    c.drawString(2*cm, y, "AÑO   MES           AGUA(m³)   GAS(m³)   COSTO(CLP)")
    y -= 0.6*cm

    for yr, mes, agua, gas, costo in _user_consumption_by_year(user, year):
        c.drawString(2*cm,   y, f"{yr}")
        c.drawString(3.5*cm, y, f"{mes}")
        c.drawRightString(10*cm, y, f"{agua:,.2f}")
        c.drawRightString(13.5*cm, y, f"{gas:,.2f}")
        c.drawRightString(18*cm, y, f"{costo:,.0f}")
        y -= 0.55*cm
        if y < 2*cm:
            c.showPage()
            y = h-2*cm

    c.showPage()
    c.save()
    return buf.getvalue()

# -------- descarga --------
@login_required
def download_consumption_report(request):
    try:
        year = int(request.GET.get("year") or datetime.date.today().year)
    except ValueError:
        raise Http404("Año inválido")

    fmt = (request.GET.get("format") or request.user.profile.report_format or "pdf").lower()
    fname = f"reporte-consumo-{slugify(request.user.username)}-{year}.{fmt}"

    if fmt == "csv":
        data = _build_csv(request.user, year)
        resp = HttpResponse(data, content_type="text/csv")
    elif fmt == "pdf":
        data = _build_pdf(request.user, year)
        resp = HttpResponse(data, content_type="application/pdf")
    else:
        raise Http404("Formato no soportado")

    resp["Content-Disposition"] = f'attachment; filename="{fname}"'
    return resp

# -------- enviar por email ahora --------
@login_required
@require_POST
def email_consumption_report(request):
    import json, datetime
    payload = json.loads(request.body or "{}")
    year = int(payload.get("year") or datetime.date.today().year)
    fmt  = (payload.get("format") or request.user.profile.report_format or "pdf").lower()
    to   = (payload.get("to") or request.user.profile.report_email or request.user.email).strip()

    if not to:
        return JsonResponse({"ok": False, "error": "No hay email de destino configurado."}, status=400)

    if fmt == "csv":
        data = _build_csv(request.user, year)
        mime = "text/csv"
    else:
        data = _build_pdf(request.user, year)
        mime = "application/pdf"

    fname = f"reporte-consumo-{slugify(request.user.username)}-{year}.{fmt}"
    email = EmailMessage(
        subject=f"Reporte de consumo {year}",
        body=f"Adjunto reporte de consumo {year} para {request.user.username}.",
        to=[to],
    )
    email.attach(fname, data, mime)
    email.send(fail_silently=False)
    return JsonResponse({"ok": True})


# accounts/views.py (ya mostrado antes)
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json
from django.http import JsonResponse

@login_required
@require_POST
def save_prefs(request):
    p = request.user.profile
    data = json.loads(request.body or "{}")

    # Campos que aceptamos
    allowed = {
        "report_frequency", "report_format", "report_email",
        # (si quieres, agrega también otros toggles existentes)
    }
    for k,v in data.items():
        if k in allowed:
            setattr(p, k, v)
    p.save()
    return JsonResponse({"ok": True})


from django.views.decorators.http import require_POST
from django.http import JsonResponse

@admin_required
@require_POST
def admin_add_consumption(request):
    import json
    try:
        payload   = json.loads(request.body or "{}")
        user_id   = int(payload["user_id"])
        year      = int(payload["year"])
        month_raw = str(payload["month"]).strip().lower()
        m3_water  = float(payload.get("m3_water") or 0)
        m3_gas    = float(payload.get("m3_gas") or 0)
        cost      = float(payload.get("cost") or 0)
    except (KeyError, ValueError, TypeError):
        return JsonResponse({"ok": False, "error": "Parámetros inválidos."}, status=400)

    # normalizar mes a abreviatura 'ene'..'dic'
    month_key = month_raw[:3]
    if month_key not in MONTH_INDEX:
        return JsonResponse({"ok": False, "error": "Mes inválido."}, status=400)

    # upsert en GasConsumption por (user, year, month)
    obj, created = GasConsumption.objects.get_or_create(
        user_id=user_id, year=year, month=month_key,
        defaults={"m3_water": m3_water, "m3_gas": m3_gas, "cost": cost},
    )
    if not created:
        obj.m3_water = m3_water
        obj.m3_gas   = m3_gas
        obj.cost     = cost
        obj.save()

    return JsonResponse({"ok": True})
