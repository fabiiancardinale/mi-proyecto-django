# ematel_site/urls.py
from django.contrib import admin
from django.urls import path
from accounts import views as acc
from accounts.api_views import MeView, consumption_series  # 👈 añade consumption_series

from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView, TokenVerifyView
)

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", acc.home, name="home"),
    path("login/", acc.login_view, name="login"),
    path("logout/", acc.logout_view, name="logout"),

    path("panel/admin/", acc.admin_dashboard, name="admin_dashboard"),
    path("panel/admin/chart-data/", acc.admin_chart_data, name="admin_chart_data"),
    path("panel/usuario/", acc.user_dashboard, name="user_dashboard"),

    path("usuarios/nuevo/", acc.create_user, name="create_user"),
    path("prefs/save/", acc.save_prefs, name="save_prefs"),
    path("report/download/", acc.download_consumption_report, name="download_report"),
    path("report/email/", acc.email_consumption_report, name="email_report"),
    path("panel/admin/consumption/add/", acc.admin_add_consumption, name="admin_add_consumption"),

    # JWT
    path("api/auth/token/",   TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(),    name="token_refresh"),
    path("api/auth/verify/",  TokenVerifyView.as_view(),     name="token_verify"),

    # API propias
    path("api/me/", MeView.as_view(), name="api_me"),
    path("api/c_series/", consumption_series, name="api_c_series"),  # 👈 NUEVO
]
