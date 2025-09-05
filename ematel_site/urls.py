# ematel_site/urls.py  (limpio)
from django.contrib import admin
from django.urls import path
from accounts import views as acc

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", acc.home, name="home"),
    path("login/", acc.login_view, name="login"),
    path("logout/", acc.logout_view, name="logout"),

    # Dashboards
    path("panel/admin/", acc.admin_dashboard, name="admin_dashboard"),
    path("panel/admin/chart-data/", acc.admin_chart_data, name="admin_chart_data"),
    path("panel/usuario/", acc.user_dashboard, name="user_dashboard"),

    # Usuarios
    path("usuarios/nuevo/", acc.create_user, name="create_user"),

    # Reportes / prefs (deja solo UNA ruta por vista)
    path("prefs/save/", acc.save_prefs, name="save_prefs"),
    path("report/download/", acc.download_consumption_report, name="download_report"),
    path("report/email/", acc.email_consumption_report, name="email_report"),

    path("panel/admin/consumption/add/", acc.admin_add_consumption, name="admin_add_consumption"),

]
