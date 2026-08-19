"""
Django settings for contratos.

Local development keeps using SQLite by default. Production can switch to MySQL
by setting DATABASE_NAME and the related DATABASE_* environment variables.
"""

import os
import sys
from pathlib import Path

try:
    from decouple import config
except ImportError:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


BASE_DIR = Path(__file__).resolve().parent.parent


def env_value(name, default=''):
    try:
        return config(name, default=default)
    except NameError:
        return os.environ.get(name, default)


def env_bool(name, default=False):
    try:
        return config(name, default=default, cast=bool)
    except NameError:
        value = os.environ.get(name, str(default))
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    return [item.strip() for item in env_value(name, default).split(',') if item.strip()]


DEBUG = env_bool('DEBUG', False)

# La clave por defecto solo existe para desarrollo (DEBUG=True). En produccion
# la aplicacion se niega a arrancar sin una SECRET_KEY real: con la clave
# publica del repositorio cualquiera podria firmar sesiones y tokens.
_SECRET_KEY_SOLO_DESARROLLO = 'django-insecure-your-secret-key-here-SOLO-DESARROLLO'
SECRET_KEY = env_value('SECRET_KEY', '') or (_SECRET_KEY_SOLO_DESARROLLO if DEBUG else '')
if not DEBUG and (not SECRET_KEY or SECRET_KEY.startswith('django-insecure')):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        'SECRET_KEY es obligatoria en produccion (DEBUG=False): defina una clave '
        'segura en el archivo .env (python -c "from django.core.management.utils '
        'import get_random_secret_key; print(get_random_secret_key())").'
    )
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'axes',
    'gestion',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'gestion.csp_middleware.ContentSecurityPolicyMiddleware',
]

ROOT_URLCONF = 'contratos.urls'

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
                'gestion.context_processors.empresa_config',
                'gestion.context_processors.admin_general_status',
            ],
        },
    },
]

WSGI_APPLICATION = 'contratos.wsgi.application'

DATABASE_NAME = env_value('DATABASE_NAME')

if DATABASE_NAME:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': DATABASE_NAME,
            'USER': env_value('DATABASE_USER'),
            'PASSWORD': env_value('DATABASE_PASSWORD'),
            'HOST': env_value('DATABASE_HOST', 'mysql'),
            'PORT': env_value('DATABASE_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 20,
            },
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# En la suite de tests no hay collectstatic: el storage con manifest fallaría
# con "Missing staticfiles manifest entry" al renderizar plantillas.
if 'test' in sys.argv:
    STORAGES['staticfiles'] = {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    }

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')

SESSION_COOKIE_AGE = 3600
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', False)
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True

AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_TEMPLATE = 'registration/login.html'
AXES_LOCKOUT_URL = None
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']
AXES_VERBOSE = False

EMAIL_BACKEND = env_value('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env_value('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(env_value('EMAIL_PORT', 587))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
EMAIL_HOST_USER = env_value('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env_value('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env_value('DEFAULT_FROM_EMAIL', 'noreply@example.com')
