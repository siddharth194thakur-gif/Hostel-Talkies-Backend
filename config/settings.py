import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from backend/.env or root .env
load_dotenv(BASE_DIR / '.env')
load_dotenv(BASE_DIR.parent / '.env')

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or os.environ.get('SECRET_KEY') or 'django-insecure-hosteltalkies-super-secret-key-2026-xyz-987'

# In production (e.g. Render / DATABASE_URL present), DEBUG must default to False unless explicitly set.
# In local development without production flags, DEBUG defaults to True.
_is_production = bool(os.environ.get('RENDER') or os.environ.get('RENDER_EXTERNAL_HOSTNAME') or os.environ.get('DATABASE_URL'))
_default_debug = 'False' if _is_production else 'True'
DEBUG = os.environ.get('DJANGO_DEBUG', os.environ.get('DEBUG', _default_debug)).lower() in ['true', '1', 'yes']

allowed_hosts_env = os.environ.get('DJANGO_ALLOWED_HOSTS', os.environ.get('ALLOWED_HOSTS', ''))
if allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(',') if h.strip()]
elif DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '.onrender.com', '.hosteltalkies.fun', 'hosteltalkies.fun', 'www.hosteltalkies.fun']

# Automatically include Render external hostname if provided
render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if render_host and render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_host)


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    
    # Local apps
    'users',
    'hostels',
    'posts',
    'notices',
    'events',
    'services',
    'study',
    'messaging',
    'notifications',
    'moderation',
    'gaming',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'users.middleware.BlockedAccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# Supports:
# 1. Individual PostgreSQL environment variables (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
# 2. DATABASE_URL (via dj_database_url or urllib with SSL support)
# 3. Automatic fallback to SQLite if remote PostgreSQL is unreachable (prevents downtime)
import urllib.parse
import socket

def is_remote_db_reachable(host, port=5432, timeout=2):
    if not host or host in ('localhost', '127.0.0.1', '0.0.0.0'):
        return True
    try:
        with socket.create_connection((host, int(port or 5432)), timeout=timeout):
            return True
    except Exception:
        return False

DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT', '5432')
DATABASE_URL = os.environ.get('DATABASE_URL')

db_configured = False

if DB_NAME and (DB_HOST or DB_USER):
    if is_remote_db_reachable(DB_HOST, DB_PORT):
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': DB_NAME,
                'USER': DB_USER or '',
                'PASSWORD': DB_PASSWORD or '',
                'HOST': DB_HOST or 'localhost',
                'PORT': DB_PORT or '5432',
                'CONN_MAX_AGE': 600,
            }
        }
        if DB_HOST and DB_HOST not in ('localhost', '127.0.0.1', '0.0.0.0'):
            DATABASES['default']['OPTIONS'] = {
                'sslmode': os.environ.get('DB_SSLMODE', 'require')
            }
        db_configured = True
    else:
        print(f"[Database Notice] PostgreSQL host {DB_HOST} is currently unreachable. Using fallback database.")

if not db_configured and DATABASE_URL:
    try:
        parsed = urllib.parse.urlparse(DATABASE_URL)
        db_host = parsed.hostname
        db_port = parsed.port or 5432
        if is_remote_db_reachable(db_host, db_port):
            import dj_database_url
            is_remote_db = not any(local in DATABASE_URL for local in ('localhost', '127.0.0.1', 'sqlite'))
            ssl_require = is_remote_db and (os.environ.get('DB_SSL_REQUIRE', 'True').lower() in ('true', '1', 'yes'))
            DATABASES = {
                'default': dj_database_url.config(
                    default=DATABASE_URL,
                    conn_max_age=600,
                    conn_health_checks=True,
                    ssl_require=ssl_require,
                )
            }
            db_configured = True
        else:
            print(f"[Database Notice] Remote database at {db_host} is unreachable. Using fallback database.")
    except Exception as exc:
        print(f"[Database Notice] Error configuring DATABASE_URL ({exc}). Using fallback database.")

if not db_configured:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Cache Configuration (5-minute TTL for player lookups)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'hosteltalkies-cache',
    }
}

# Free Fire API Provider Configuration
FREEFIRE_API_BASE_URL = os.environ.get('FREEFIRE_API_BASE_URL', '').strip()
FREEFIRE_API_KEY = os.environ.get('FREEFIRE_API_KEY', '').strip()

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email Configuration (Loaded strictly from environment variables)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com').strip()
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587') or 587)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '').strip()
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '').strip()
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')

env_from = os.environ.get('DEFAULT_FROM_EMAIL', '').strip()
if env_from:
    DEFAULT_FROM_EMAIL = env_from
elif EMAIL_HOST_USER:
    DEFAULT_FROM_EMAIL = f'HostelTalkies <{EMAIL_HOST_USER}>'
else:
    DEFAULT_FROM_EMAIL = 'HostelTalkies <no-reply@hosteltalkies.com>'

# Use SMTP if credentials are provided, allow explicit EMAIL_BACKEND override, fallback to console backend in debug mode
env_backend = os.environ.get('EMAIL_BACKEND', '').strip()
if env_backend:
    EMAIL_BACKEND = env_backend
elif EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
elif DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'users.authentication.LenientJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '120/minute',
        'user': '1200/minute',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Simple JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=90),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,  # Blacklist app not installed; logout handled client-side
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
}

# CORS & CSRF Settings
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'https://hostel-talkies.vercel.app',
    'https://hostel-talkies-frontend.vercel.app',
    'https://www.hosteltalkies.fun',
    'https://hosteltalkies.fun',
]
extra_cors = os.environ.get('CORS_ALLOWED_ORIGINS', '')
if extra_cors:
    CORS_ALLOWED_ORIGINS.extend([origin.strip() for origin in extra_cors.split(',') if origin.strip()])

CORS_ALLOW_ALL_ORIGINS = False

# Allow all Vercel deployment preview subdomains and custom domain variants automatically
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
    r"^https://(.*?\.)?hosteltalkies\.fun$",
]

CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://localhost:3000',
    'http://127.0.0.1:8000',
    'https://*.onrender.com',
    'https://*.vercel.app',
    'https://*.netlify.app',
    'https://*.railway.app',
    'https://www.hosteltalkies.fun',
    'https://hosteltalkies.fun',
    'https://*.hosteltalkies.fun',
]
extra_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if extra_csrf:
    CSRF_TRUSTED_ORIGINS.extend([origin.strip() for origin in extra_csrf.split(',') if origin.strip()])



