from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-xxx"   # mueve esto a variables de entorno en cuanto puedas
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]  # agrega tu dominio/IP pública cuando despliegues

INSTALLED_APPS = [
    "monitoring.apps.MonitoringConfig",
    "accounts",  # <-- nuestra app
    "django.contrib.humanize",   # <--- AGREGA ESTA LÍNEA
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ematel_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # <-- carpeta templates común
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ematel_site.wsgi.application"

# === Base de datos (tu config) ===
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "calderas_ematel",
        "USER": "datasensor_farmacia",
        "PASSWORD": "Ematel2025*",
        "HOST": "82.25.79.89",
        "PORT": "3306",
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            "charset": "utf8mb4",
        },
    }
}

# Usuario personalizado (roles)
AUTH_USER_MODEL = "accounts.User"

# Login/Logout
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

# Internacionalización (Chile)
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# Static
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]  # opcional, si tendrás /static con css/js
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Si accedes por IP/dominio en producción, agrega también (ajusta host):
# CSRF_TRUSTED_ORIGINS = ["https://tudominio.cl", "https://82.25.79.89"]
BASE_DIR = Path(__file__).resolve().parent.parent

# Archivos estáticos
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),  # tus CSS/JS en desarrollo
]

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")  # carpeta destino para collectstatic