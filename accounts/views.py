# accounts/views.py
"""Vistas del panel EMATEL.

Las vistas solo hacen tres cosas: validar la entrada, delegar en la capa de
servicios y armar el contexto de la plantilla. La logica de negocio vive en
``accounts.services``, el manejo de meses en ``accounts.months`` y la
generacion de reportes en ``accounts.reports``.
"""

from __future__ import annotations

import datetime
import json
from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import months, reports, services
from .forms import (
    AdminCreateUserForm,
    AdminEditUserForm,
    AdminGasConsumptionForm,
    GasConsumptionForm,
    PreferenciasReporteForm,
    ProfileForm,
    ProfilePanelForm,
)
from .models import GasConsumption, Profile, User

# =============================================================================
# Permisos por rol
# =============================================================================
def redirect_by_role(user) -> str:
    """Nombre de la ruta a la que corresponde enviar a este usuario."""
    if getattr(user, "is_superuser", False):
        return "admin_dashboard"
    return "admin_dashboard" if user.is_admin() else "user_dashboard"


def role_required(*roles):
    """Restringe una vista a ciertos roles.

    Compara siempre contra los codigos internos ("admin"/"user"), nunca contra
    las etiquetas visibles. Los superusuarios pasan siempre.
    """
    roles_permitidos = {str(r).strip().casefold() for r in roles}

    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if getattr(request.user, "is_superuser", False):
                return vista(request, *args, **kwargs)

            rol = (getattr(request.user, "role", "") or "").strip().casefold()
            if rol not in roles_permitidos:
                return redirect(redirect_by_role(request.user))
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador


admin_required = role_required(User.Roles.ADMIN)
user_required = role_required(User.Roles.USER, User.Roles.ADMIN)


# =============================================================================
# Autenticacion
# =============================================================================
class LoginForm(forms.Form):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect(redirect_by_role(request.user))

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if usuario is not None:
            login(request, usuario)
            return redirect(redirect_by_role(usuario))
        form.add_error(None, "Credenciales inválidas.")

    return render(request, "login.html", {"form": form})


def home(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect(redirect_by_role(request.user))
    return render(request, "home.html")


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("login")


# =============================================================================
# Panel de administracion
# =============================================================================
def _entero_o_none(valor) -> int | None:
    return int(valor) if valor and str(valor).isdigit() else None


def _filtros_de_usuarios(request: HttpRequest):
    """Aplica busqueda, rol y estado al listado de usuarios."""
    texto = (request.GET.get("q") or "").strip()
    rol = (request.GET.get("role") or "").strip()
    estado = (request.GET.get("status") or "").strip()

    usuarios = User.objects.select_related("profile").order_by("id")
    if texto:
        usuarios = usuarios.filter(
            Q(username__icontains=texto) | Q(email__icontains=texto)
        )
    if rol in dict(User.Roles.choices):
        usuarios = usuarios.filter(role=rol)
    if estado == "activos":
        usuarios = usuarios.filter(is_active=True)
    elif estado == "inactivos":
        usuarios = usuarios.filter(is_active=False)

    return usuarios, texto, rol, estado


@admin_required
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    """Panel de administracion: usuarios, comparativas y alta de consumo."""
    hoy = timezone.localdate()
    anio_actual, anio_previo = hoy.year, hoy.year - 1

    admin_form = AdminGasConsumptionForm(request.POST or None)

    if request.method == "POST":
        if admin_form.is_valid():
            datos = admin_form.cleaned_data
            try:
                registro, _ = services.registrar_consumo(
                    user=datos["user"],
                    year=datos["year"],
                    month=datos.get("month_choice"),
                    day=datos.get("day"),
                    m3_water=datos.get("m3_water"),
                    m3_gas=datos.get("m3_gas"),
                    cost=datos.get("cost"),
                )
            except services.MesInvalido as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request,
                    f"Consumo guardado para {registro.user.username} "
                    f"({registro.month_label} {registro.year}).",
                )
                return redirect(f"{request.path}?selected_user={registro.user_id}#consumo")
        else:
            messages.error(request, "Revisa los datos del formulario.")

    # ---- Usuario seleccionado para tabla y graficos ----
    selected_user_id = request.GET.get("selected_user")
    id_seleccionado = _entero_o_none(selected_user_id)

    chart_data = services.datos_comparativa(
        user_id=id_seleccionado,
        anio_actual=anio_actual,
        anio_previo=anio_previo,
    )

    # ---- Registros del usuario seleccionado ----
    filas, totales, anio_tabla = [], {}, None
    if id_seleccionado:
        usuario_sel = User.objects.filter(pk=id_seleccionado).first()
        if usuario_sel:
            filas = services.historial(usuario_sel)
            anio_tabla = filas[0].year if filas else None
            totales = services.resumen_anual(usuario_sel, anio_tabla)

    # ---- Listado de usuarios ----
    usuarios, texto, rol, estado = _filtros_de_usuarios(request)
    paginador = Paginator(usuarios, 10)
    pagina = paginador.get_page(request.GET.get("page"))

    # Filtros serializados para que la paginacion no los pierda.
    filtros = QueryDict(mutable=True)
    for clave, valor in (("q", texto), ("role", rol), ("status", estado)):
        if valor:
            filtros[clave] = valor
    if selected_user_id:
        filtros["selected_user"] = selected_user_id
    filtros_qs = filtros.urlencode()
    if filtros_qs:
        filtros_qs += "&"

    return render(request, "admin_dashboard.html", {
        "chart_data": chart_data,
        "admin_form": admin_form,
        "selected_user_id": selected_user_id,
        "rows": filas,
        "year_now_tbl": anio_tabla,
        "totals": totales,
        "users_for_filter": User.objects.order_by("username").only("id", "username"),
        "page_obj": pagina,
        "paginator": paginador,
        "q": texto,
        "role_filter": rol,
        "status_filter": estado,
        "filtros_qs": filtros_qs,
        "total_users": User.objects.count(),
        "total_activos": User.objects.filter(is_active=True).count(),
        "total_inactivos": User.objects.filter(is_active=False).count(),
        "total_sin_link": Profile.objects.filter(
            Q(link="") | Q(link__isnull=True)
        ).count(),
    })


@admin_required
def admin_chart_data(request: HttpRequest) -> JsonResponse:
    """Datos de los graficos para un usuario, o globales si no se indica."""
    hoy = timezone.localdate()
    try:
        anio_actual = int(request.GET.get("year_now") or hoy.year)
        anio_previo = int(request.GET.get("year_prev") or anio_actual - 1)
    except ValueError:
        return JsonResponse({"ok": False, "error": "Año inválido."}, status=400)

    return JsonResponse({"chart_data": services.datos_comparativa(
        user_id=_entero_o_none(request.GET.get("user_id")),
        anio_actual=anio_actual,
        anio_previo=anio_previo,
    )})


@admin_required
@require_POST
def admin_add_consumption(request: HttpRequest) -> JsonResponse:
    """Alta de consumo por JSON, para integraciones externas."""
    try:
        datos = json.loads(request.body or "{}")
        usuario = User.objects.get(pk=int(datos["user_id"]))
        anio = int(datos["year"])
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Parámetros inválidos."}, status=400)
    except User.DoesNotExist:
        return JsonResponse({"ok": False, "error": "El usuario no existe."}, status=404)

    try:
        registro, creado = services.registrar_consumo(
            user=usuario,
            year=anio,
            month=datos.get("month"),
            day=datos.get("day"),
            m3_water=datos.get("m3_water"),
            m3_gas=datos.get("m3_gas"),
            cost=datos.get("cost"),
        )
    except services.MesInvalido as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    return JsonResponse({"ok": True, "id": registro.id, "creado": creado})


# =============================================================================
# Panel de usuario
# =============================================================================
@user_required
def user_dashboard(request: HttpRequest) -> HttpResponse:
    """Panel del cliente: su consumo, comparativas y reportes."""
    usuario = request.user
    perfil = getattr(usuario, "profile", None)

    if request.method == "POST":
        form = GasConsumptionForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                services.registrar_consumo(
                    user=usuario,
                    year=datos["year"],
                    month=datos.get("month_choice"),
                    day=datos.get("day"),
                    m3_water=datos.get("m3_water"),
                    m3_gas=datos.get("m3_gas"),
                )
            except services.MesInvalido as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Consumo guardado correctamente.")
                return redirect("user_dashboard")
        else:
            messages.error(request, "Revisa los datos del formulario.")
    else:
        form = GasConsumptionForm()

    filas = services.historial(usuario)
    anio_actual = filas[0].year if filas else None
    resumen = services.resumen_anual(usuario, anio_actual)

    # ---- Busqueda de un mes puntual ----
    anios = services.anios_disponibles(usuario)
    anio_pedido = _entero_o_none(request.GET.get("year")) or anio_actual
    mes_pedido = (request.GET.get("month") or "").strip()
    registro, comparativa = services.buscar_mes(usuario, anio_pedido, mes_pedido)

    return render(request, "user_dashboard.html", {
        "profile": perfil,
        "form": form,
        "rows": filas,
        "year_now": anio_actual,
        "totals": resumen,
        "avg_current": {
            "water_avg": resumen["water_avg"],
            "gas_avg": resumen["gas_avg"],
        },
        "years_available": anios,
        "months_available": list(months.NOMBRES),
        "selected_year": anio_pedido,
        "selected_month": mes_pedido,
        "current_entry": registro,
        "yoy": comparativa,
    })


# =============================================================================
# Gestion de usuarios
# =============================================================================
@admin_required
def create_user(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        uform = AdminCreateUserForm(request.POST)
        pform = ProfileForm(request.POST)

        if uform.is_valid() and pform.is_valid():
            with transaction.atomic():
                usuario = uform.save(commit=False)
                usuario.role = uform.cleaned_data["role"]
                usuario.is_staff = False
                usuario.is_superuser = False
                usuario.save()

                # La señal post_save ya creo el perfil: lo completamos.
                perfil, _ = Profile.objects.get_or_create(user=usuario)
                ProfileForm(request.POST, instance=perfil).save()

            messages.success(request, f"Usuario '{usuario.username}' creado correctamente.")
            return redirect("admin_dashboard")

        messages.error(request, "Revisa los campos, hay errores en el formulario.")
    else:
        uform = AdminCreateUserForm()
        pform = ProfileForm()

    return render(request, "register_user.html", {"uform": uform, "pform": pform})


@admin_required
@require_POST
def editar_usuario(request: HttpRequest, pk: int) -> JsonResponse:
    """Actualiza cuenta y perfil desde el modal del panel.

    Devuelve los errores campo por campo para que el modal los muestre.
    """
    usuario = get_object_or_404(User, pk=pk)
    perfil, _ = Profile.objects.get_or_create(user=usuario)

    uform = AdminEditUserForm(request.POST, instance=usuario)
    pform = ProfilePanelForm(request.POST, instance=perfil)

    if not (uform.is_valid() and pform.is_valid()):
        errores = {
            **{c: [str(e) for e in lista] for c, lista in uform.errors.items()},
            **{c: [str(e) for e in lista] for c, lista in pform.errors.items()},
        }
        return JsonResponse({"ok": False, "errores": errores}, status=400)

    # Un admin no puede dejarse fuera del panel a si mismo.
    if usuario == request.user:
        if not uform.cleaned_data.get("is_active"):
            return JsonResponse(
                {"ok": False, "errores": {"is_active": ["No puedes desactivar tu propia cuenta."]}},
                status=400,
            )
        if uform.cleaned_data.get("role") != User.Roles.ADMIN:
            return JsonResponse(
                {"ok": False, "errores": {"role": ["No puedes quitarte tu propio rol de administrador."]}},
                status=400,
            )

    with transaction.atomic():
        uform.save()
        pform.save()

    messages.success(request, f"Usuario '{usuario.username}' actualizado correctamente.")
    return JsonResponse({"ok": True})


@admin_required
@require_POST
def eliminar_usuario(request: HttpRequest, pk: int) -> HttpResponse:
    usuario = get_object_or_404(User, pk=pk)

    if usuario == request.user:
        messages.error(request, "No puedes eliminar tu propia cuenta.")
        return redirect("admin_dashboard")

    nombre = usuario.username
    try:
        usuario.delete()
        messages.success(request, f"Usuario '{nombre}' eliminado correctamente.")
    except ProtectedError:
        messages.error(
            request,
            "No se puede eliminar: tiene registros asociados "
            "(protegido por integridad referencial).",
        )
    return redirect("admin_dashboard")


@admin_required
def lista_usuarios(request: HttpRequest) -> HttpResponse:
    """El listado con filtros y paginacion vive en el panel de admin.

    Esta ruta apuntaba a una plantilla inexistente. Se mantiene para no romper
    enlaces guardados.
    """
    return redirect(f"{reverse('admin_dashboard')}#usuarios")


# =============================================================================
# Reportes y preferencias
# =============================================================================
def _anio_pedido(valor) -> int:
    try:
        return int(valor) if valor else datetime.date.today().year
    except (TypeError, ValueError):
        raise Http404("Año inválido")


@user_required
def download_consumption_report(request: HttpRequest) -> HttpResponse:
    anio = _anio_pedido(request.GET.get("year"))
    formato = request.GET.get("format") or request.user.profile.report_format

    try:
        contenido, mime, nombre = reports.construir(request.user, anio, formato)
    except reports.FormatoNoSoportado:
        raise Http404("Formato no soportado")
    except reports.ReportlabNoInstalado as exc:
        return HttpResponse(str(exc), status=503, content_type="text/plain; charset=utf-8")

    respuesta = HttpResponse(contenido, content_type=mime)
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta


@user_required
@require_POST
def email_consumption_report(request: HttpRequest) -> JsonResponse:
    try:
        datos = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Petición inválida."}, status=400)

    perfil = request.user.profile
    anio = _anio_pedido(datos.get("year"))
    formato = datos.get("format") or perfil.report_format
    destino = (datos.get("to") or perfil.report_email or request.user.email or "").strip()

    if not destino:
        return JsonResponse(
            {"ok": False, "error": "No hay email de destino configurado."}, status=400
        )

    try:
        contenido, mime, nombre = reports.construir(request.user, anio, formato)
    except reports.FormatoNoSoportado:
        return JsonResponse({"ok": False, "error": "Formato no soportado."}, status=400)
    except reports.ReportlabNoInstalado as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=503)

    correo = EmailMessage(
        subject=f"Reporte de consumo {anio}",
        body=f"Adjunto el reporte de consumo {anio} para {request.user.username}.",
        to=[destino],
    )
    correo.attach(nombre, contenido, mime)

    try:
        correo.send(fail_silently=False)
    except Exception as exc:  # el backend SMTP puede fallar por mil razones
        return JsonResponse(
            {"ok": False, "error": f"No se pudo enviar el correo: {exc}"}, status=502
        )

    return JsonResponse({"ok": True})


@user_required
@require_POST
def save_prefs(request: HttpRequest) -> JsonResponse:
    """Guarda las preferencias de reporte del usuario."""
    try:
        datos = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Petición inválida."}, status=400)

    perfil = request.user.profile
    formulario = PreferenciasReporteForm(datos, instance=perfil)

    if not formulario.is_valid():
        return JsonResponse(
            {"ok": False, "errores": {c: [str(e) for e in l]
                                      for c, l in formulario.errors.items()}},
            status=400,
        )

    formulario.save()
    return JsonResponse({"ok": True})


# =============================================================================
# Errores
# =============================================================================
def custom_404(request: HttpRequest, exception) -> HttpResponse:
    return render(request, "404.html", status=404)
