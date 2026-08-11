from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga las variables desde .env (no versionado). Ver .env.example.
load_dotenv(BASE_DIR / ".env")


def env(clave, defecto=None, *, requerido=False):
    valor = os.getenv(clave, defecto)
    if requerido and not valor:
        raise RuntimeError(
            f"Falta la variable de entorno {clave}. "
            f"Copia .env.example a .env y completala."
        )
    return valor


def env_bool(clave, defecto=False):
    valor = os.getenv(clave)
    if valor is None:
        return defecto
    return valor.strip().lower() in {"1", "true", "yes", "on", "si"}


def env_list(clave, defecto=""):
    return [x.strip() for x in os.getenv(clave, defecto).split(",") if x.strip()]


# =============================
# Seguridad
# =============================
DEBUG = env_bool("DJANGO_DEBUG", False)

# En desarrollo se permite una clave temporal; en produccion es obligatoria.
SECRET_KEY = env("DJANGO_SECRET_KEY", requerido=not DEBUG) or "dev-only-insecure-key"

# Sin comodines: cada host se declara explicitamente.
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Endurecimiento que reportaba `manage.py check --deploy`.
# Solo se activa fuera de desarrollo para no romper el trabajo local en http.
if not DEBUG:
    SESSION_COOKIE_SECURE = env_bool("DJANGO_COOKIES_SEGURAS", True)
    CSRF_COOKIE_SECURE = env_bool("DJANGO_COOKIES_SEGURAS", True)
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SSL_REDIRECT", False)
    SECURE_HSTS_SECONDS = int(env("DJANGO_HSTS_SEGUNDOS", "0"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
    SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

INSTALLED_APPS = [
    "monitoring.apps.MonitoringConfig",
    "accounts",
    "django.contrib.humanize",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # necesario con DEBUG=False
    "corsheaders.middleware.CorsMiddleware",        # antes de CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =============================
# CORS (solo aplica a /api/)
# =============================
from corsheaders.defaults import default_headers  # noqa: E402

CORS_URLS_REGEX = r"^/api/.*$"
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ORIGINS")
CORS_ALLOW_HEADERS = list(default_headers) + ["authorization", "content-type"]

ROOT_URLCONF = "ematel_site.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]

WSGI_APPLICATION = "ematel_site.wsgi.application"

# =============================
# Base de datos
# =============================
if env_bool("DJANGO_USAR_SQLITE", False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("DB_NOMBRE", requerido=True),
            "USER": env("DB_USUARIO", requerido=True),
            "PASSWORD": env("DB_PASSWORD", requerido=True),
            "HOST": env("DB_HOST", "127.0.0.1"),
            "PORT": env("DB_PUERTO", "3306"),
            "OPTIONS": {
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
                "charset": "utf8mb4",
            },
        }
    }

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# =============================
# Estaticos
# =============================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# STORAGES reemplaza a STATICFILES_STORAGE, obsoleto desde Django 4.2.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================
# Correo (reportes de consumo)
# =============================
if env("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = int(env("EMAIL_PUERTO", "587"))
    EMAIL_HOST_USER = env("EMAIL_USUARIO", "")
    EMAIL_HOST_PASSWORD = env("EMAIL_PASSWORD", "")
    EMAIL_USE_TLS = env_bool("EMAIL_USAR_TLS", True)
else:
    # Sin SMTP configurado los correos se imprimen en consola en vez de
    # fallar con un error de conexion.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = env("EMAIL_REMITENTE", "no-reply@ematel.cl")

# =============================
# DRF + JWT
# =============================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}
