"""API de administración que usa la app móvil (solo administradores).

Rutas (prefijo /api/):
  admin/resumen/      GET     indicadores y clientes que requieren atención
  clientes/           GET     listado (?q=, ?role=admin|user, ?status=activos|inactivos)
                      POST    crear cliente (cuenta + perfil)
  clientes/<id>/      GET     ficha completa
                      PATCH   editar cuenta y perfil (solo los campos enviados)
                      DELETE  eliminar (también borra su consumo)

Usa los mismos formularios que el panel web, así que las reglas de
validación son idénticas en ambos lados.
"""

import datetime

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from .forms import AdminCreateUserForm, AdminEditUserForm, ProfileForm
from .models import Profile, User


def es_admin(user) -> bool:
    return bool(user.is_authenticated and (user.is_superuser or user.is_admin()))


class EsAdmin(BasePermission):
    message = "Solo para administradores."

    def has_permission(self, request, view):
        return es_admin(request.user)


def _iso(fecha):
    return fecha.isoformat() if fecha else None


def ficha(u: User) -> dict:
    """Datos de un usuario y su perfil, tal como los muestra la app."""
    p = getattr(u, "profile", None)
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email or "",
        "role": u.role,
        "es_admin": es_admin(u),
        "is_active": u.is_active,
        "date_joined": _iso(u.date_joined),
        "last_login": _iso(u.last_login),
        "location": p.location if p else "",
        "external_id": p.external_id if p else "",
        "manager_name": p.manager_name if p else "",
        "phone": p.phone if p else "",
        "address": p.address if p else "",
        "link": p.link if p else "",
        "tiene_link": bool(p and p.link),
        "last_maintenance": _iso(p.last_maintenance) if p else None,
        "next_maintenance": _iso(p.next_maintenance) if p else None,
        "days_to_next_maintenance": p.days_to_next_maintenance if p else None,
        "maintenance_interval_months": p.maintenance_interval_months if p else 12,
    }


def _errores(*formularios) -> dict:
    return {
        campo: [str(e) for e in lista]
        for f in formularios
        for campo, lista in f.errors.items()
    }


CAMPOS_USUARIO = ("username", "email", "role", "is_active")
CAMPOS_PERFIL = (
    "location", "external_id", "manager_name", "phone", "address", "link",
    "last_maintenance", "next_maintenance", "maintenance_interval_months",
)


# ---------------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated, EsAdmin])
def resumen(request):
    """Indicadores del panel y la lista de clientes que requieren atención."""
    conteo = User.objects.aggregate(
        total=Count("id"),
        activos=Count("id", filter=Q(is_active=True)),
    )
    conteo["inactivos"] = conteo["total"] - conteo["activos"]

    # Solo clientes: los superusuarios pueden tener rol "user" pero no lo son.
    clientes = User.objects.filter(
        role=User.Roles.USER, is_active=True, is_superuser=False
    ).select_related("profile")
    sin_link = clientes.filter(Q(profile__link="") | Q(profile__link__isnull=True))
    limite = timezone.localdate() + datetime.timedelta(days=30)
    mantencion = clientes.filter(profile__next_maintenance__lte=limite).order_by("profile__next_maintenance")

    conteo["sin_link"] = sin_link.count()
    conteo["mantencion_vencida"] = mantencion.filter(profile__next_maintenance__lt=timezone.localdate()).count()
    conteo["mantencion_proxima"] = mantencion.count() - conteo["mantencion_vencida"]

    return Response({
        "conteo": conteo,
        "mantencion": [ficha(u) for u in mantencion[:20]],
        "sin_link": [ficha(u) for u in sin_link.order_by("username")[:20]],
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, EsAdmin])
def clientes(request):
    if request.method == "POST":
        return _crear(request)

    usuarios = User.objects.select_related("profile").order_by("username")
    texto = (request.GET.get("q") or "").strip()
    if texto:
        usuarios = usuarios.filter(
            Q(username__icontains=texto) | Q(email__icontains=texto) | Q(profile__location__icontains=texto)
        )
    rol = request.GET.get("role")
    if rol in (User.Roles.ADMIN, User.Roles.USER):
        usuarios = usuarios.filter(role=rol)
    estado = request.GET.get("status")
    if estado == "activos":
        usuarios = usuarios.filter(is_active=True)
    elif estado == "inactivos":
        usuarios = usuarios.filter(is_active=False)

    return Response([ficha(u) for u in usuarios])


def _crear(request):
    datos = request.data
    uform = AdminCreateUserForm(datos)
    pform = ProfileForm(datos)
    if not (uform.is_valid() and pform.is_valid()):
        return Response({"errores": _errores(uform, pform)}, status=400)

    with transaction.atomic():
        usuario = uform.save(commit=False)
        usuario.role = uform.cleaned_data["role"]
        usuario.is_staff = False
        usuario.is_superuser = False
        usuario.save()
        perfil, _ = Profile.objects.get_or_create(user=usuario)
        ProfileForm(datos, instance=perfil).save()

    usuario.refresh_from_db()
    return Response(ficha(usuario), status=201)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, EsAdmin])
def cliente(request, pk: int):
    usuario = get_object_or_404(User.objects.select_related("profile"), pk=pk)

    if request.method == "GET":
        return Response(ficha(usuario))

    if request.method == "DELETE":
        if usuario == request.user:
            return Response({"detail": "No puedes eliminar tu propia cuenta."}, status=400)
        usuario.delete()
        return Response(status=204)

    return _editar(request, usuario)


def _editar(request, usuario: User):
    """PATCH: solo cambian los campos enviados; el resto conserva su valor."""
    perfil, _ = Profile.objects.get_or_create(user=usuario)
    actual = ficha(usuario)
    datos = request.data

    datos_usuario = {c: datos.get(c, actual[c]) for c in CAMPOS_USUARIO}
    datos_perfil = {c: datos.get(c, actual[c]) for c in CAMPOS_PERFIL}
    datos_perfil = {c: ("" if v is None else v) for c, v in datos_perfil.items()}
    # Si cambia la última mantención y no se indica la próxima, se recalcula.
    if "last_maintenance" in datos and "next_maintenance" not in datos:
        datos_perfil["next_maintenance"] = ""
    # El BooleanField de Django interpreta "False" como texto verdadero.
    if datos_usuario["is_active"] in (False, "false", "False", 0, "0", ""):
        datos_usuario.pop("is_active")

    uform = AdminEditUserForm(datos_usuario, instance=usuario)
    pform = ProfileForm(datos_perfil, instance=perfil)
    if not (uform.is_valid() and pform.is_valid()):
        return Response({"errores": _errores(uform, pform)}, status=400)

    if usuario == request.user:
        if not uform.cleaned_data.get("is_active"):
            return Response({"errores": {"is_active": ["No puedes desactivar tu propia cuenta."]}}, status=400)
        if not usuario.is_superuser and uform.cleaned_data.get("role") != User.Roles.ADMIN:
            return Response({"errores": {"role": ["No puedes quitarte tu propio rol de administrador."]}}, status=400)

    with transaction.atomic():
        uform.save()
        pform.save()

    usuario.refresh_from_db()
    return Response(ficha(usuario))
