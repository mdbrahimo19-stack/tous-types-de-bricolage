"""Configuration Django - projet TTB (backend MVP)."""
from datetime import timedelta
from pathlib import Path
import json
import os
import sys

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(key, default=False):
    return os.getenv(key, str(default)).lower() in {"1", "true", "yes", "on"}


# --- Sécurité de base -------------------------------------------------------
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY", "dev-insecure-change-me-0000000000000000000000000000000000000000"
)
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
if DEBUG:
    # En développement, le serveur est joint par l'IP du PC, qui change avec le Wi-Fi
    # (téléphone réel, émulateur 10.0.2.2…) : on accepte toutes les adresses.
    # En production (DEBUG=False), seule la liste DJANGO_ALLOWED_HOSTS s'applique.
    ALLOWED_HOSTS = ["*"]

# --- Applications ----------------------------------------------------------
INSTALLED_APPS = [
    "apps.dashboard.admin_config.TTBAdminConfig",  # admin Django + tableau de bord
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # tiers
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "phonenumber_field",
    # locales
    "apps.accounts",
    "apps.catalog",
    "apps.locations",
    "apps.marketplace",
    "apps.billing",
    "apps.ai",
    "apps.dashboard",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# --- Base de données -------------------------------------------------------
DATABASES = {
    "default": dj_database_url.parse(
        os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n / temps --------------------------------------------------------
LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", "Français"), ("ar", "العربية")]
TIME_ZONE = "Africa/Algiers"
USE_I18N = True
USE_TZ = True

# --- Fichiers statiques / médias ---------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Téléphone ----------------------------------------------------------
PHONENUMBER_DEFAULT_REGION = "DZ"
PHONENUMBER_DB_FORMAT = "E164"

# --- DRF --------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.ScopedRateThrottle",),
    "DEFAULT_THROTTLE_RATES": {"otp": "5/hour", "auth": "20/hour", "requests": "60/hour", "ai": "30/hour"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

# --- CORS ------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]

# --- OTP / SMS -----------------------------------------------------
SMS_BACKEND = os.getenv("SMS_BACKEND", "console")  # console | http (fournisseur SMS) | firebase
# Réglages du backend `http` (voir apps/accounts/sms.py et docs/sms-aggregator-brief.md)
SMS_API_URL = os.getenv("SMS_API_URL", "")
SMS_API_KEY = os.getenv("SMS_API_KEY", "")
SMS_AUTH_HEADER = os.getenv("SMS_AUTH_HEADER", "Authorization")
SMS_AUTH_SCHEME = os.getenv("SMS_AUTH_SCHEME", "Bearer")
SMS_SENDER_ID = os.getenv("SMS_SENDER_ID", "")
SMS_PHONE_FORMAT = os.getenv("SMS_PHONE_FORMAT", "e164")  # e164 (+213…) | intl (213…) | local (0…)
SMS_FIELD_TO = os.getenv("SMS_FIELD_TO", "to")
SMS_FIELD_TEXT = os.getenv("SMS_FIELD_TEXT", "text")
SMS_FIELD_SENDER = os.getenv("SMS_FIELD_SENDER", "sender")
SMS_EXTRA_JSON = json.loads(os.getenv("SMS_EXTRA_JSON") or "{}")
SMS_TIMEOUT_SECONDS = int(os.getenv("SMS_TIMEOUT_SECONDS", "10"))
PUSH_BACKEND = os.getenv("PUSH_BACKEND", "console")  # console | fcm
OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "300"))
OTP_LENGTH = 6
OTP_MAX_ATTEMPTS = 5
OTP_EXPOSE_IN_RESPONSE = DEBUG  # confort dev : renvoie le code dans la réponse API
FIREBASE_CREDENTIALS_FILE = os.getenv("FIREBASE_CREDENTIALS_FILE", "")

# --- Règles métier (paramétrables) --------------------------------
REQUEST_EXPIRY_DAYS = 7
MAX_ACTIVE_REQUESTS_PER_CLIENT = 5
QUOTE_VALIDITY_HOURS = 72

# Envoi des demandes aux bricoleurs les plus proches (GPS), par vagues :
# la 1re vague part aux N plus proches ; sans devis au bout de X minutes,
# la demande passe aux N suivants (au plus DISPATCH_MAX_WAVES vagues).
DISPATCH_BATCH_SIZE = int(os.environ.get("DISPATCH_BATCH_SIZE", 5))
DISPATCH_WAVE_MINUTES = int(os.environ.get("DISPATCH_WAVE_MINUTES", 15))
DISPATCH_MAX_WAVES = int(os.environ.get("DISPATCH_MAX_WAVES", 4))

# Points des bricoleurs : chaque client qui accepte un devis coûte 25 points (1 point = 10 DA).
# 50 points offerts à l'inscription ; à 200 points dus (2 000 DA) le compte est bloqué
# jusqu'au paiement BaridiMob validé par l'administrateur.
POINTS_PER_CONTACT = int(os.environ.get("POINTS_PER_CONTACT", 25))
POINT_VALUE_DA = int(os.environ.get("POINT_VALUE_DA", 10))
POINTS_WELCOME_FREE = int(os.environ.get("POINTS_WELCOME_FREE", 50))
POINTS_BLOCK_AT = int(os.environ.get("POINTS_BLOCK_AT", 200))
# Compte BaridiMob qui reçoit les paiements (affiché aux bricoleurs dans l'app)
BARIDIMOB_RIP = os.environ.get("BARIDIMOB_RIP", "")
BARIDIMOB_NAME = os.environ.get("BARIDIMOB_NAME", "")
# Adresse qui reçoit un email à chaque capture de paiement envoyée
PAYMENTS_NOTIFY_EMAIL = os.environ.get("PAYMENTS_NOTIFY_EMAIL", "")

# Paiement des points par carte Edahabia / CIB via Chargily Pay (https://chargily.com).
# Sans clé secrète, le bouton « Payer par carte » est masqué (BaridiMob reste disponible).
CHARGILY_SECRET_KEY = os.environ.get("CHARGILY_SECRET_KEY", "")
CHARGILY_MODE = os.environ.get("CHARGILY_MODE", "test")  # test | live
# Adresse publique HTTPS du serveur (ex. https://api.bricool.dz) : Chargily y envoie
# la confirmation de paiement (webhook). Vide en local : vérification au retour dans l'app.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

# --- Email (console en dev : les emails s'affichent dans le terminal) ---
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "noreply@localhost")

# --- IA (Claude / Anthropic) -------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "claude-opus-5-5")
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "60"))
# Sans clé, l'IA est désactivée : endpoints /api/ai/ -> 503, modération ignorée (fail-open).
# Jamais d'appel réel pendant `manage.py test` (coût + tests non déterministes).
AI_ENABLED = env_bool("AI_ENABLED", bool(ANTHROPIC_API_KEY)) and "test" not in sys.argv

# Noms de cookies propres au projet : évite les conflits avec d'autres projets
# servis sur la même adresse (ex. un ancien `csrftoken` resté dans le navigateur).
CSRF_COOKIE_NAME = "ttb_csrftoken"
SESSION_COOKIE_NAME = "ttb_sessionid"

# Origines HTTPS autorisées pour les formulaires (admin derrière Caddy), ex. https://api.exemple.dz
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# --- Sécurité prod ------------------------------------------------
if not DEBUG:
    # vérification de santé de Docker, lancée depuis le conteneur lui-même (http://localhost:8000)
    if "localhost" not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append("localhost")
    SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
