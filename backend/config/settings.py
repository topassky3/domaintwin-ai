import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-domaintwin-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]
INSTALLED_APPS = ["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","core"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","core.auth_middleware.PrivateApiSessionMiddleware","core.rbac.RoleAuthorizationMiddleware","core.tenant_middleware.TenantDomainBoundaryMiddleware","django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware"]
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

# The historical deterministic regression suite predates login enforcement. During
# `manage.py test` it keeps exercising those paths without session setup, while
# dedicated P2/P3 security tests override this to False and verify production
# authentication, RBAC and tenant boundaries explicitly.
DOMAIN_TWIN_TESTING = any(arg == "test" for arg in sys.argv)

# P2 authentication uses Django's server-side session framework. The browser only
# receives an opaque HttpOnly session cookie. CSRF tokens are bootstrapped through
# an authenticated API boundary instead of reading the CSRF cookie from JavaScript.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = int(os.getenv("DJANGO_SESSION_COOKIE_AGE_SECONDS", str(60 * 60 * 24 * 14)))
_SECURE_COOKIES = os.getenv("DJANGO_SECURE_COOKIES", "0") == "1"
SESSION_COOKIE_SECURE = _SECURE_COOKIES
CSRF_COOKIE_SECURE = _SECURE_COOKIES

NAMECOM_ENVIRONMENT = os.getenv("NAMECOM_ENVIRONMENT", "sandbox").strip().lower()
NAMECOM_USERNAME = os.getenv("NAMECOM_USERNAME", "").strip()
NAMECOM_API_TOKEN = os.getenv("NAMECOM_API_TOKEN", "").strip()
NAMECOM_TIMEOUT_SECONDS = float(os.getenv("NAMECOM_TIMEOUT_SECONDS", "10"))
NAMECOM_ALLOW_MUTATIONS = os.getenv("NAMECOM_ALLOW_MUTATIONS", "0") == "1"
NAMECOM_ALLOW_PRODUCTION_MUTATIONS = os.getenv("NAMECOM_ALLOW_PRODUCTION_MUTATIONS", "0") == "1"
# Gate 8 registration is intentionally sandbox-only. DNS mutation permission is
# not enough: this second switch must also be enabled for the sandbox drill.
NAMECOM_ALLOW_DOMAIN_REGISTRATION = os.getenv("NAMECOM_ALLOW_DOMAIN_REGISTRATION", "0") == "1"

DOMAIN_HEALTH_TIMEOUT_SECONDS = float(os.getenv("DOMAIN_HEALTH_TIMEOUT_SECONDS", "4"))

# Evidence-based AI incident explanations. Disabled by default so core DNS detection
# and recovery never depend on an external AI provider.
AI_PROVIDER = os.getenv("AI_PROVIDER", "disabled").strip().lower()
AI_MODEL = os.getenv("AI_MODEL", "gpt-5.6-luna").strip()
AI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "15"))
AI_MAX_OUTPUT_TOKENS = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "700"))
