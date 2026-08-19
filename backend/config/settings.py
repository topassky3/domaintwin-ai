import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-domaintwin-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]
INSTALLED_APPS = ["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","core"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default":{"ENGINE":"django.db.backends.sqlite3","NAME":BASE_DIR / "db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

NAMECOM_ENVIRONMENT = os.getenv("NAMECOM_ENVIRONMENT", "sandbox").strip().lower()
NAMECOM_USERNAME = os.getenv("NAMECOM_USERNAME", "").strip()
NAMECOM_API_TOKEN = os.getenv("NAMECOM_API_TOKEN", "").strip()
NAMECOM_TIMEOUT_SECONDS = float(os.getenv("NAMECOM_TIMEOUT_SECONDS", "10"))
NAMECOM_ALLOW_MUTATIONS = os.getenv("NAMECOM_ALLOW_MUTATIONS", "0") == "1"
NAMECOM_ALLOW_PRODUCTION_MUTATIONS = os.getenv("NAMECOM_ALLOW_PRODUCTION_MUTATIONS", "0") == "1"

DOMAIN_HEALTH_TIMEOUT_SECONDS = float(os.getenv("DOMAIN_HEALTH_TIMEOUT_SECONDS", "4"))

# Evidence-based AI incident explanations. Disabled by default so core DNS detection
# and recovery never depend on an external AI provider.
AI_PROVIDER = os.getenv("AI_PROVIDER", "disabled").strip().lower()
AI_MODEL = os.getenv("AI_MODEL", "gpt-5.6-luna").strip()
AI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "15"))
AI_MAX_OUTPUT_TOKENS = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "700"))
