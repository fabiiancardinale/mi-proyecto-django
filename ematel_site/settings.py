import io
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent



def _cargar_env(ruta: Path) -> None:
    """Carga el archivo .env (no versionado; ver .env.example).

    En Windows, ``echo X=1 > .env`` desde PowerShell guarda el archivo en
    UTF-16 y python-dotenv falla con UnicodeDecodeError. Aqui se detecta la
    codificacion por su marca inicial para que funcione igual.
    """
    if not ruta.exists():
        return
    crudo = ruta.read_bytes()
    if crudo.startswith((b"\xff\xfe", b"\xfe\xff")):
        texto = crudo.decode("utf-16")
    else:
        texto = crudo.decode("utf-8-sig")
    load_dotenv(stream=io.StringIO(texto))


_cargar_env(BASE_DIR / ".env")


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
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Terceros
    "rest_framework",
    "corsheaders",
    # Proyecto
    "accounts.apps.AccountsConfig",
    "monitoring.apps.MonitoringConfig",
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

# En produccion los estaticos llevan hash en el nombre (cache infinita), lo que
# exige correr collectstatic. En desarrollo y en los tests se sirven tal cual:
# antes los tests fallaban con "Missing staticfiles manifest entry".
EJECUTANDO_TESTS = len(sys.argv) > 1 and sys.argv[1] == "test"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or EJECUTANDO_TESTS
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
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

# Duracion de los tokens de la app movil: el access caduca rapido y la app lo
# renueva sola con el refresh, que dura un mes para no pedir login a diario.
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}
