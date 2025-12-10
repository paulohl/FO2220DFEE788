"""
Django settings for autofacebook project.

🔥 MEJORADO: Incluye configuración de Celery Beat y logging mejorado
"""

from pathlib import Path
import os
import pytz
import time
from celery.schedules import crontab

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Ruta donde se guardarán los archivos subidos (imágenes, etc.)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# URL base para servir archivos de medios
MEDIA_URL = '/code/media/'

STATIC_URL = 'static/'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-)zft%eh^2wo9u#5+l@57)fa3sifksgnbulf&&sy!98siq!i2mp'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    'publicadorFacebook',
    'revolico',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'autofacebook.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'autofacebook.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es-es'
TIME_ZONE = os.environ.get('DJANGO_TIME_ZONE', 'America/Havana')

# Alinear la zona horaria del sistema operativo y los procesos secundarios
# (Django, Celery, Playwright) para evitar desfases de una hora.
os.environ.setdefault('TZ', TIME_ZONE)
try:
    time.tzset()
except AttributeError:
    # No disponible en algunas plataformas (por ejemplo, Windows)
    pass
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# 🔥 CONFIGURACIÓN DE CELERY MEJORADA
# ============================================================================

CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = False

environment = "docker"
if environment == "docker":
    CELERY_BROKER_URL = 'redis://redis:6379/0'
    CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
else:
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# 🔥 NUEVO: Tareas periódicas con Celery Beat
CELERY_BEAT_SCHEDULE = {
    'limpiar-tareas-vencidas': {
        'task': 'publicadorFacebook.tasks.limpiar_tareas_vencidas',
        'schedule': crontab(minute=0),  # Cada hora
        'options': {'expires': 3600}
    },
    'verificar-salud-sistema': {
        'task': 'publicadorFacebook.tasks.verificar_salud_sistema',
        'schedule': crontab(minute='*/30'),  # Cada 30 minutos
        'options': {'expires': 1800}
    },
}

# Configuración adicional de Celery
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutos
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50

# ============================================================================
# 🔥 CONFIGURACIÓN DE CACHÉ Y FACEBOOK
# ============================================================================

FACEBOOK_CACHE_DIR = os.path.join(BASE_DIR, 'facebook_cache')
os.makedirs(FACEBOOK_CACHE_DIR, exist_ok=True)

# Directorio para screenshots
FACEBOOK_SCREENSHOTS_DIR = os.path.join(BASE_DIR, 'capturas')
os.makedirs(FACEBOOK_SCREENSHOTS_DIR, exist_ok=True)

# Cache Redis para Django
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/1' if environment == "docker" else 'redis://localhost:6379/1',
        'KEY_PREFIX': 'facebook_automation',
        'TIMEOUT': 86400,  # 24 horas
    }
}

# ============================================================================
# 🔥 CONFIGURACIÓN DE LOGGING MEJORADA
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'publicadorFacebook': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}

os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
