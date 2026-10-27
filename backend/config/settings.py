"""Réglages Django de l'application Gestion Atelier.

Par défaut la démo tourne sur SQLite. Si la variable POSTGRES_DB est définie
(cas du docker-compose), PostgreSQL est utilisé.
"""
import os
import warnings
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# Racine du dépôt : backend/ contient le code Python, frontend/ les gabarits HTML,
# les feuilles de style et le JavaScript.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"

# Sans variable d'environnement, c'est la démo locale (DEBUG). Une installation réelle met DJANGO_DEBUG=0
# et doit alors fournir sa propre clé secrète et la liste des adresses du serveur (voir docker-compose.yml).
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "demo-cle-non-secrete" if DEBUG else "")
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY est obligatoire quand DJANGO_DEBUG=0.")
ALLOWED_HOSTS = [hote for hote in os.environ.get("DJANGO_ALLOWED_HOSTS", "*" if DEBUG else "").split(",") if hote]
if not ALLOWED_HOSTS and not DEBUG:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS est obligatoire quand DJANGO_DEBUG=0 (ex. « atelier.local,192.168.1.20 »).")

# Derrière HTTPS (DJANGO_HTTPS=1) : cookies réservés à HTTPS et navigateur prévenu de ne plus passer en HTTP.
# Le port 8000 ne doit alors être joignable que par le proxy HTTPS, qui seul pose X-Forwarded-Proto.
if os.environ.get("DJANGO_HTTPS") == "1":
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "comptes",
    "inventaire",
    "outillage",
    "produits",
    "commandes",
    "remontees",
    "production",
    "aide",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Sert les feuilles de style et le JavaScript quand gunicorn tourne seul (Docker).
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "comptes.middleware.ConnexionObligatoireMiddleware",
    "comptes.middleware.DroitsDeConsultationMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [FRONTEND_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "comptes.context_processors.profil",
                "aide.context_processors.aide",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "atelier"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "db"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            # Les écritures attendent leur tour au lieu d'échouer sur « database is locked » (double clic).
            "OPTIONS": {"transaction_mode": "IMMEDIATE"},
        }
    }

# Règles des mots de passe choisis dans l'application ; les comptes de démo (« demo ») sont créés sans elles.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "connexion"
LOGIN_REDIRECT_URL = "accueil"
LOGOUT_REDIRECT_URL = "connexion"

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [FRONTEND_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# Avant collectstatic (tests, export de la démo), le dossier n'existe pas : whitenoise le signale sans raison.
warnings.filterwarnings("ignore", message="No directory at", module="whitenoise.base")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Rendu destiné à l'export statique (GitHub Pages) : bandeau de démo et saisies simulées.
DEMO_STATIQUE = os.environ.get("DEMO_STATIQUE") == "1"

TEST_RUNNER = "config.test_runner.LanceurTests"

# Documents et photos déposés sur les fiches. Sur la VM, ce dossier est un volume Docker (voir docker-compose.yml).
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))
MEDIA_URL = "media/"
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
FILE_UPLOAD_HANDLERS = [
    "produits.envois.LimiteTailleEnvoi",
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]
