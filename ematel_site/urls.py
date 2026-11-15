"""Rutas del proyecto EMATEL.

Las vistas HTML viven en ``accounts.views`` y la API REST en
``accounts.api_url``, montada bajo ``/api/``.
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from accounts import views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Sesión
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Paneles
    path("panel/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("panel/admin/chart-data/", views.admin_chart_data, name="admin_chart_data"),
    path("panel/admin/consumption/add/", views.admin_add_consumption, name="admin_add_consumption"),
    path("panel/usuario/", views.user_dashboard, name="user_dashboard"),

    # Gestión de usuarios
    path("usuarios/", views.lista_usuarios, name="usuarios_lista"),
    path("usuarios/nuevo/", views.create_user, name="create_user"),
    path("usuarios/<int:pk>/editar/", views.editar_usuario, name="usuario_editar"),
    path("usuarios/<int:pk>/eliminar/", views.eliminar_usuario, name="usuario_eliminar"),

    # Reportes y preferencias
    path("prefs/save/", views.save_prefs, name="save_prefs"),
    path("report/download/", views.download_consumption_report, name="download_report"),
    path("report/email/", views.email_consumption_report, name="email_report"),

    # API (JWT)
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/", include("accounts.api_url")),
]

handler404 = "accounts.views.custom_404"
