"""
Paramètres Django de MemoAI Pro.

Toutes les valeurs sensibles (clé secrète, base de données, clés IA, Stripe...)
viennent du fichier .env à la racine du projet (jamais versionné).
"""

import os
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [v.strip() for v in os.environ.get(name, default).split(',') if v.strip()]


# Vercel : VERCEL n'est présent que si les variables système sont exposées. Les fonctions Vercel
# s'exécutent toujours depuis /var/task : ce repère fonctionne dans tous les cas.
ON_VERCEL = bool(
    os.environ.get('VERCEL')
    or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
    or BASE_DIR.as_posix().startswith('/var/task')
)

# Sur Vercel, DEBUG est désactivé par défaut : une variable oubliée ne doit jamais
# afficher la page d'erreur détaillée de Django au public.
DEBUG = env_bool('DEBUG', not ON_VERCEL)

SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('SECRET_KEY doit être défini dans .env en production.')
    SECRET_KEY = 'django-insecure-dev-only-change-me'

def clean_host(value):
    """« https://exemple.vercel.app/ » → « exemple.vercel.app » (erreur de saisie fréquente)."""
    return value.split('://', 1)[-1].split('/', 1)[0].strip().lower()


ALLOWED_HOSTS = [clean_host(h) for h in env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')]

# Vercel : adresses du déploiement (si les variables système sont exposées)...
for _var in ('VERCEL_URL', 'VERCEL_BRANCH_URL', 'VERCEL_PROJECT_PRODUCTION_URL'):
    if os.environ.get(_var):
        ALLOWED_HOSTS.append(clean_host(os.environ[_var]))
# ... et, dans tous les cas, les sous-domaines vercel.app : Vercel n'achemine vers ce projet
# que les requêtes adressées à ses propres domaines, un en-tête Host étranger ne peut donc pas l'atteindre.
if ON_VERCEL:
    ALLOWED_HOSTS.append('.vercel.app')

if ON_VERCEL:
    # Diagnostic visible dans les logs Vercel à chaque démarrage (aucune valeur secrète affichée).
    print(
        f"[MemoAI] démarrage Vercel : DEBUG={DEBUG} ALLOWED_HOSTS={ALLOWED_HOSTS} "
        f"SECRET_KEY={'oui' if os.environ.get('SECRET_KEY') else 'NON'} "
        f"DATABASE_URL={'oui' if os.environ.get('DATABASE_URL') else 'NON'} "
        f"VERCEL={'oui' if os.environ.get('VERCEL') else 'non'} BASE_DIR={BASE_DIR}",
        file=sys.stderr, flush=True,
    )


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
    # Fichiers statiques (admin Django, Swagger) servis par l'application elle-même (Vercel).
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
    'config.security.SecurityHeadersMiddleware',
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

TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    # Fermé par défaut : une vue publique doit le déclarer explicitement (AllowAny).
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    # Pas d'interface « navigable » de DRF en production (elle expose la structure de l'API).
    'DEFAULT_RENDERER_CLASSES': (
        ('rest_framework.renderers.JSONRenderer', 'rest_framework.renderers.BrowsableAPIRenderer')
        if DEBUG else ('rest_framework.renderers.JSONRenderer',)
    ),
    # Limitation du nombre de requêtes (force brute, robots, abus de l'IA).
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.environ.get('THROTTLE_ANON', '60/min'),
        'user': os.environ.get('THROTTLE_USER', '600/min'),
        'login': os.environ.get('THROTTLE_LOGIN', '10/min'),        # par adresse IP
        'register': os.environ.get('THROTTLE_REGISTER', '5/hour'),
        'refresh': '30/min',
        'two_factor': '10/hour',
        'password': '10/hour',
        'password_reset': '5/hour',          # demandes d'email par adresse IP
        'password_reset_confirm': '20/hour',
        'shared': '30/min',
        'ai': os.environ.get('THROTTLE_AI', '150/hour'),  # « Rédiger le mémoire » : un appel par chapitre
        'upload': '60/hour',
        'payment_declare': '15/hour',        # déclarations de paiement par client
    },
    # Vercel : l'adresse réelle du visiteur est la première de X-Forwarded-For.
    'NUM_PROXIES': 1 if ON_VERCEL else None,
}
if TESTING:  # les tests de limitation fixent leurs propres seuils
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {k: '10000/min' for k in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']}

# Verrouillage d'un compte après trop d'échecs de connexion (quelle que soit l'adresse IP).
LOGIN_MAX_FAILURES = int(os.environ.get('LOGIN_MAX_FAILURES', '8'))
LOGIN_LOCKOUT_MINUTES = int(os.environ.get('LOGIN_LOCKOUT_MINUTES', '15'))

# Compteurs (limitation, verrouillage) partagés entre toutes les instances Vercel : stockés en base.
# Table créée par « python manage.py createcachetable ».
CACHES = {
    'default': (
        {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'} if TESTING or not os.environ.get('DATABASE_URL')
        else {'BACKEND': 'django.core.cache.backends.db.DatabaseCache', 'LOCATION': 'memoai_cache'}
    ),
}

# Connexion Google : désactivée tant que l'identifiant client OAuth n'est pas défini.
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

# Chemin de l'administration Django : à personnaliser (ex. ADMIN_URL=gestion-7f3k/) pour la cacher des robots.
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin/').strip('/') + '/'
# Documentation Swagger / ReDoc : uniquement en développement, sauf ENABLE_API_DOCS=1.
ENABLE_API_DOCS = env_bool('ENABLE_API_DOCS', DEBUG)

AUTH_USER_MODEL = 'users.User'
AUTHENTICATION_BACKENDS = ['users.security.LockoutModelBackend']

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
# Déploiements de prévisualisation Vercel du frontend (ex. https://memoai-git-xxx.vercel.app).
CORS_ALLOWED_ORIGIN_REGEXES = env_list('CORS_ALLOWED_ORIGIN_REGEXES')

# Formulaires de l'admin Django en HTTPS (Vercel) : origines de confiance pour la protection CSRF.
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS') + [
    f'https://{h}' if not h.startswith('.') else f'https://*{h}'
    for h in ALLOWED_HOSTS if h not in ('localhost', '127.0.0.1', '*')
]


# ---------------------------------------------------------------- base de données

def database_from_url(url):
    """postgresql://user:motdepasse@hote/base?sslmode=require (format fourni par Neon)."""
    parts = urlparse(url)
    if parts.scheme not in ('postgres', 'postgresql'):
        raise ImproperlyConfigured('DATABASE_URL doit être une URL PostgreSQL (postgresql://...).')
    options = dict(parse_qsl(parts.query))
    options.setdefault('sslmode', 'require')
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(parts.path.lstrip('/')),
        'USER': unquote(parts.username or ''),
        'PASSWORD': unquote(parts.password or ''),
        'HOST': parts.hostname or '',
        'PORT': str(parts.port or 5432),
        'OPTIONS': options,
        # Serverless : pas de connexion persistante entre deux requêtes (Neon met la base en veille).
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '0')),
        'CONN_HEALTH_CHECKS': True,
    }


# Production (Neon) : DATABASE_URL. Développement : variables DB_* du fichier .env.
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
if DATABASE_URL:
    DATABASES = {'default': database_from_url(DATABASE_URL)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'memoai'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
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

# API de paiement de MemoAI (modeles/mobile_money.py) : les clients paient directement sur ce numéro
# par Orange Money, Moov Money ou Wave. Vide : le paiement passe par Jɛmɛnipay.
PAYMENT_NUMBER = '' if TESTING else os.environ.get('PAYMENT_NUMBER', '').strip()
# Numéro propre à un opérateur, s'il diffère : PAYMENT_NUMBER_ORANGE, PAYMENT_NUMBER_MOOV, PAYMENT_NUMBER_WAVE.
PAYMENT_NUMBERS = {} if TESTING else {
    operator: os.environ.get(f'PAYMENT_NUMBER_{operator.upper()}', '').strip() for operator in ('orange', 'moov', 'wave')}
PAYMENT_HOLDER = os.environ.get('PAYMENT_HOLDER', '').strip()  # nom du bénéficiaire, affiché au client
PAYMENT_NOTIFY_EMAILS = env_list('PAYMENT_NOTIFY_EMAILS')  # vide : tous les administrateurs

# Jɛmɛnipay : paiement des modèles de mémoire (page de paiement hébergée).
# Le mode découle de la clé publique : pk_live_… = argent réel, pk_test_… = bac à sable (paiements simulés).
JEMENI_PUBLIC_KEY = os.environ.get('JEMENI_PUBLIC_KEY', '').strip()
JEMENI_SECRET_KEY = os.environ.get('JEMENI_SECRET_KEY', '').strip()
JEMENI_TOKEN = os.environ.get('JEMENI_TOKEN', '').strip()  # jeton utilisateur
JEMENI_WEBHOOK_SECRET = os.environ.get('JEMENI_WEBHOOK_SECRET', '').strip()
JEMENI_API_URL = os.environ.get('JEMENI_API_URL', 'https://jemeni.net/api')
JEMENI_COUNTRY = os.environ.get('JEMENI_COUNTRY', 'ml')
# Paiements simulés (clés de test) : jamais en production, sinon les modèles seraient gratuits pour tous.
JEMENI_ALLOW_SANDBOX = env_bool('JEMENI_ALLOW_SANDBOX', not ON_VERCEL)
MODELE_PRICE = os.environ.get('MODELE_PRICE', '5000')  # prix d'un modèle (XOF) à sa création

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
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
EMAIL_TIMEOUT = 15
# Lien « mot de passe oublié » : valable 1 heure.
PASSWORD_RESET_TIMEOUT = int(os.environ.get('PASSWORD_RESET_TIMEOUT', '3600'))
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'MemoAI Pro <no-reply@memoai.local>')


# ---------------------------------------------------------------- sécurité des mots de passe

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Tests uniquement : hachage rapide des mots de passe (le PBKDF2 réel rend la suite très lente).
if TESTING:
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


# ---------------------------------------------------------------- langue, fichiers

LANGUAGE_CODE = 'fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
# Dossier rempli seulement par « collectstatic » (inutile sur Vercel grâce à WhiteNoise).
STATIC_ROOT = BASE_DIR / 'staticfiles' if 'collectstatic' in sys.argv or (BASE_DIR / 'staticfiles').is_dir() else None
# Sans étape collectstatic (Vercel) : WhiteNoise lit directement les fichiers statiques des applications.
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG
# Fichiers envoyés par les utilisateurs : dossier dédié, jamais la racine du projet
# (sinon .env et le code source seraient téléchargeables).
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Taille maximale d'une requête (images des figures en base64) : Vercel refuse au-delà de 4,5 Mo.
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000

# ---------------------------------------------------------------- production (HTTPS)

if not DEBUG:
    # Vercel termine le HTTPS en amont et transmet le protocole d'origine.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    # HTTPS obligatoire pour les navigateurs pendant un an.
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_AGE = 60 * 60 * 8  # administration Django : session de 8 heures

SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
