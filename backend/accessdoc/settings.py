"""
Django settings for accessdoc project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _default_accessdoc_repo_and_utils() -> tuple[Path, Path]:
    """
    Resolve AccessDoc repo root and ``backend/utils`` from ``Path.cwd()`` + relative paths.

    Supports common invocations:

    - ``cd backend && python manage.py …`` → repo = ``cwd.parent``, utils = ``cwd / "utils"``
    - ``cd <repo> && python backend/manage.py …`` → repo = ``cwd``, utils = ``cwd / "backend/utils"``

    Falls back to layout implied by this file (``accessdoc/settings.py`` → ``backend/`` → repo).
    """
    cwd = Path.cwd().resolve()
    if (cwd / "manage.py").is_file():
        return cwd.parent.resolve(), (cwd / "utils").resolve()
    if (cwd / "backend" / "manage.py").is_file():
        return cwd.resolve(), (cwd / "backend" / "utils").resolve()
    repo = BASE_DIR.parent.resolve()
    return repo, (BASE_DIR / "utils").resolve()


_CWD_REPO_ROOT, _CWD_UTILS_DIR = _default_accessdoc_repo_and_utils()

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-change-in-production",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

# Railway injects ``RAILWAY_PUBLIC_DOMAIN`` (e.g. ``accessdoc-production.up.railway.app``) when
# public networking is enabled — add it so Host / CSRF checks match the browser URL.
_railway_public_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
if _railway_public_domain and _railway_public_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, _railway_public_domain]

# HTTPS production: comma-separated full origins (scheme + host, optional port). Required for many
# POST/login flows in Django 4+ when the site is not localhost. Example:
#   DJANGO_CSRF_TRUSTED_ORIGINS=https://app.example.com,https://www.example.com
_csrf_trusted = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").strip()
CSRF_TRUSTED_ORIGINS = [
    o.strip().rstrip("/") for o in _csrf_trusted.split(",") if o.strip()
]
if _railway_public_domain:
    _railway_origin = f"https://{_railway_public_domain}".rstrip("/")
    if _railway_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS = [*CSRF_TRUSTED_ORIGINS, _railway_origin]

# nginx / Traefik / cloud LB terminates TLS — without this, Django sees http:// and CSRF/session
# cookies marked Secure may not align with what the browser sends.
# On Railway, HTTPS is at the edge: default to proxy headers when ``RAILWAY_PUBLIC_DOMAIN`` is set,
# unless ``DJANGO_BEHIND_PROXY`` is explicitly false.
_behind_proxy = os.environ.get("DJANGO_BEHIND_PROXY", "").strip().lower()
if _behind_proxy in ("0", "false", "no"):
    _use_proxy_headers = False
elif _behind_proxy in ("1", "true", "yes"):
    _use_proxy_headers = True
else:
    _use_proxy_headers = bool(_railway_public_domain)

if _use_proxy_headers:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

# In production (DEBUG off), use Secure cookies when the site is served over HTTPS.
if not DEBUG:
    _insecure_cookies = os.environ.get("DJANGO_INSECURE_COOKIES", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if not _insecure_cookies:
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "items.apps.ItemsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "accessdoc.middleware.AccessDocWhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "accessdoc.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "accessdoc.wsgi.application"

# Optional shared DB dir (e.g. Docker volume mounted at the same path on web + Celery worker).
_sqlite_dir = os.environ.get("ACCESSDOC_SQLITE_DIR", "").strip()
_sqlite_path = (
    Path(_sqlite_dir) / "db.sqlite3" if _sqlite_dir else BASE_DIR / "db.sqlite3"
)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _sqlite_path,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise: Django static files; ``index.html`` inside route dirs matches typical static hosts.
WHITENOISE_INDEX_FILE = True
WHITENOISE_ALLOW_ALL_ORIGINS = True

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"

REPO_ROOT = Path(
    os.environ.get("ACCESSDOC_REPO_ROOT", str(_CWD_REPO_ROOT))
).resolve()
UTILS_DIR = Path(
    os.environ.get(
        "ACCESSDOC_UTILS_DIR",
        os.environ.get("ACCESSDOC_SCRIPTS_DIR", str(_CWD_UTILS_DIR)),
    )
).resolve()
# Shared Docusaurus builder (source is replaced on each publish).
DOCUSAURUS_ROOT = Path(
    os.environ.get("ACCESSDOC_DOCUSAURUS_ROOT", REPO_ROOT / "demo_docs")
).resolve()
# Each ready item gets ``demo_docs/build/`` copied under ``DOCUSAURUS_BUILDS_ROOT``;
# default: ``backend/templates/doc_builds/<PublishedItem.pk>/`` (upload id = UUID folder name).
DOCUSAURUS_BUILDS_ROOT = Path(
    os.environ.get(
        "ACCESSDOC_DOCUSAURUS_BUILDS_ROOT",
        str(BASE_DIR / "templates" / "doc_builds"),
    )
).resolve()

DOCUSAURUS_BASE_URL = os.environ.get("DOCUSAURUS_BASE_URL", "/viewer/")

DOCUSAURUS_BUILD_DIR = Path(
    os.environ.get("ACCESSDOC_DOCUSAURUS_BUILD_DIR", DOCUSAURUS_ROOT / "build")
).resolve()

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0"
)
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "3600"))

# When False, PDF processing runs in a background thread after DB commit (no Redis worker needed).
# When True, use ``celery -A accessdoc worker`` and Redis. Defaults: threaded in DEBUG, Celery when not DEBUG.
_ACCESSDOC_USE_CELERY_RAW = os.environ.get("ACCESSDOC_USE_CELERY")
if _ACCESSDOC_USE_CELERY_RAW is not None:
    ACCESSDOC_USE_CELERY = _ACCESSDOC_USE_CELERY_RAW.lower() in ("1", "true", "yes")
else:
    ACCESSDOC_USE_CELERY = not DEBUG

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

DASHBOARD_POLL_INTERVAL_MS = int(
    os.environ.get("ACCESSDOC_DASHBOARD_POLL_MS", "2500")
)

MAX_UPLOAD_BYTES = int(os.environ.get("ACCESSDOC_MAX_UPLOAD_MB", "25")) * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = min(MAX_UPLOAD_BYTES, 50 * 1024 * 1024)
FILE_UPLOAD_MAX_MEMORY_SIZE = min(MAX_UPLOAD_BYTES, 50 * 1024 * 1024)
