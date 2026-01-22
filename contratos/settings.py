"""
Django settings for contratos project.
ADVERTENCIA: Este archivo es para DESARROLLO solamente.
Para producción, usa settings_production.py
"""

import os
from pathlib import Path

# Cargar variables de entorno desde .env (si existe)
try:
    from decouple import config
    # python-decouple cargará automáticamente el archivo .env
    # Usar config() en lugar de os.environ.get() para cargar desde .env
except ImportError:
    # Si decouple no está instalado, cargar manualmente con dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        # Si no hay soporte para .env, usar solo variables de entorno del sistema
        pass

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# En desarrollo usamos una clave fija, en producción debe venir de variable de entorno
# Usar config() si decouple está disponible, sino os.environ.get()
try:
    SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-secret-key-here-SOLO-DESARROLLO')
except NameError:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-secret-key-here-SOLO-DESARROLLO')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # Para formateo de números y fechas
    'axes',  # Protección contra fuerza bruta
    'gestion',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'axes.middleware.AxesMiddleware',  # Protección contra fuerza bruta
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'gestion.middleware.LicenseCheckMiddleware',  # Verificar licencia en cada request
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
                'gestion.context_processors.license_status',
            ],
        },
    },
]

WSGI_APPLICATION = 'contratos.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# CSRF Trusted Origins (importante para producción)
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if os.environ.get('CSRF_TRUSTED_ORIGINS') else []

# Configuración de Seguridad de Sesiones
SESSION_COOKIE_AGE = 3600  # 1 hora en segundos
SESSION_COOKIE_HTTPONLY = True  # Previene acceso a cookies desde JavaScript (protección XSS)
SESSION_COOKIE_SAMESITE = 'Strict'  # Protección CSRF mejorada
SESSION_SAVE_EVERY_REQUEST = True  # Renueva la sesión en cada request
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Expira la sesión al cerrar el navegador
SESSION_COOKIE_SECURE = False  # Solo True en producción con HTTPS

# Configuración de django-axes (Protección contra fuerza bruta)
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5  # Número de intentos fallidos antes de bloquear
AXES_COOLOFF_TIME = 1  # Tiempo de bloqueo en horas (1 hora)
AXES_LOCKOUT_TEMPLATE = 'registration/login.html'  # Template a mostrar cuando está bloqueado
AXES_LOCKOUT_URL = None  # Usar template en lugar de URL
AXES_RESET_ON_SUCCESS = True  # Resetear contador al hacer login exitoso
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']  # Bloquear por combinación usuario+IP
AXES_VERBOSE = False  # Logging detallado (desactivado para reducir ruido en logs)

# Configuración de Email (se puede sobrescribir desde ConfiguracionEmail en BD)
# En producción, la configuración se toma desde el modelo ConfiguracionEmail
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')