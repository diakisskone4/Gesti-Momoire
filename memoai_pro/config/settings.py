"""
Paramètres Django de MemoAI Pro.

Toutes les valeurs sensibles (clé secrète, base de données, clés IA, Stripe...)
viennent du fichier .env à la racine du projet (jamais versionné).
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [v.strip() for v in os.environ.get(name, default).split(',') if v.strip()]


DEBUG = env_bool('DEBUG', True)

SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('SECRET_KEY doit être défini dans .env en production.')
    SECRET_KEY = 'django-insecure-dev-only-change-me'

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')


# ---------------------------------------------------------------- applications

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'channels',
    'users',
    'projects',
    'documents',
    'ai',
    'payments',
    'exports',
    'collaborations',
    'notifications',
    'admin_dashboard',
    'modeles',
    'drf_yasg',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Doit rester APRES AuthenticationMiddleware : sinon request.user n'existe
    # pas encore pour les requetes preflight OPTIONS court-circuitees par
    # CorsMiddleware avant d'atteindre AuthenticationMiddleware.
    'users.middleware.ActivityLogMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# ---------------------------------------------------------------- API & authentification

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

AUTH_USER_MODEL = 'users.User'

# Jetons JWT : le frontend renouvelle l'accès automatiquement avec le jeton de
# rafraîchissement, qui change à chaque renouvellement (l'ancien est blacklisté).
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# Code secret exigé pour s'inscrire en tant qu'administrateur.
# Vide = inscription administrateur désactivée (utiliser createsuperuser).
ADMIN_REGISTRATION_CODE = os.environ.get('ADMIN_REGISTRATION_CODE', '')

# Frontend React (Vite : port 5173 en développement)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173').rstrip('/')
CORS_ALLOWED_ORIGINS = sorted({
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    FRONTEND_URL,
    *env_list('CORS_EXTRA_ORIGINS'),
})
# Nom du fichier exporté lisible par le frontend (téléchargements).
CORS_EXPOSE_HEADERS = ['Content-Disposition']


# ---------------------------------------------------------------- base de données

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'memoai'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'Diakis7261'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}


# ---------------------------------------------------------------- Redis, Celery, Channels

# REDIS_URL vide = mode développement sans Redis :
# - les tâches Celery s'exécutent directement dans la requête ;
# - les notifications temps réel passent par une couche mémoire (un seul processus).
REDIS_URL = os.environ.get('REDIS_URL', '').strip()

CELERY_BROKER_URL = REDIS_URL or 'memory://'
CELERY_RESULT_BACKEND = REDIS_URL or 'cache+memory://'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TASK_ALWAYS_EAGER = env_bool('CELERY_TASK_ALWAYS_EAGER', not REDIS_URL)

if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [REDIS_URL]},
        },
    }
else:
    CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


# ---------------------------------------------------------------- services externes

# Stripe
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# SasPay : paiement des modèles de mémoire (mobile money / carte, checkout hébergé)
SASPAY_SECRET_KEY = os.environ.get('SASPAY_SECRET_KEY', '')
SASPAY_API_URL = os.environ.get('SASPAY_API_URL', 'https://api.saspay.me/api/v1')
SASPAY_WEBHOOK_SECRET = os.environ.get('SASPAY_WEBHOOK_SECRET', '')
SASPAY_DEFAULT_COUNTRY = os.environ.get('SASPAY_DEFAULT_COUNTRY', 'ML')  # pays présélectionné sur la page de paiement
MODELE_PRICE = os.environ.get('MODELE_PRICE', '15500')  # prix d'un modèle (XOF) à sa création

# IA : fournisseur au choix — "openrouter" (API compatible OpenAI) ou "anthropic" (API Claude)
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'openrouter')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://openrouter.ai/api/v1')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
AI_MODEL = os.environ.get('AI_MODEL', 'openai/gpt-4' if AI_PROVIDER == 'openrouter' else 'claude-opus-5-5')
# OpenRouter : modèles de secours, séparés par des virgules (utilisés si AI_MODEL est saturé)
AI_FALLBACK_MODELS = env_list('AI_FALLBACK_MODELS')
# Pause (secondes) avant de réessayer quand tous les modèles sont saturés (429).
AI_SATURATION_RETRY_DELAY = float(os.environ.get('AI_SATURATION_RETRY_DELAY', '3'))

# Emails (codes 2FA...) : affichés dans la console en développement.
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '25'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', False)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'MemoAI Pro <no-reply@memoai.local>')


# ---------------------------------------------------------------- sécurité des mots de passe

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Tests uniquement : hachage rapide des mots de passe (le PBKDF2 réel rend la suite très lente).
if len(sys.argv) > 1 and sys.argv[1] == 'test':
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


# ---------------------------------------------------------------- langue, fichiers

LANGUAGE_CODE = 'fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Fichiers envoyés par les utilisateurs : dossier dédié, jamais la racine du projet
# (sinon .env et le code source seraient téléchargeables).
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
