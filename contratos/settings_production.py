"""
Configuración de Django para PRODUCCIÓN
"""

import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY no está configurada. "
        "Por favor, configura la variable de entorno SECRET_KEY antes de ejecutar en producción. "
        "Ejemplo: export SECRET_KEY='tu-clave-secreta-super-segura'"
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Application definition
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

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

# SQLite: Adecuada para proyectos pequeños-medianos (< 50 usuarios simultáneos)
# MySQL: Disponible en PythonAnywhere desde plan Hacker ($5/mes)
# Ver docs/deployment/BASES_DATOS_PYTHONANYWHERE.md para más información

# Configuración para SQLite (gratis en PythonAnywhere)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Configuración alternativa para MySQL (descomentar si migras a MySQL)
# Requiere: Plan Hacker ($5/mes) o superior en PythonAnywhere
# Requiere: pip install mysqlclient
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': os.environ.get('DATABASE_NAME', 'tu_usuario$nombre_db'),
#         'USER': os.environ.get('DATABASE_USER', 'tu_usuario'),
#         'PASSWORD': os.environ.get('DATABASE_PASSWORD', ''),
#         'HOST': os.environ.get('DATABASE_HOST', 'tu_usuario.mysql.pythonanywhere-services.com'),
#         'PORT': os.environ.get('DATABASE_PORT', '3306'),
#         'OPTIONS': {
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#             'charset': 'utf8mb4',
#         },
#     }
# }

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración de Seguridad de Sesiones
SESSION_COOKIE_AGE = 3600  # 1 hora en segundos
SESSION_COOKIE_HTTPONLY = True  # Previene acceso a cookies desde JavaScript (protección XSS)
SESSION_COOKIE_SAMESITE = 'Strict'  # Protección CSRF mejorada
SESSION_SAVE_EVERY_REQUEST = True  # Renueva la sesión en cada request
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Expira la sesión al cerrar el navegador

# Configuración de django-axes (Protección contra fuerza bruta)
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5  # Número de intentos fallidos antes de bloquear
AXES_COOLOFF_TIME = 1  # Tiempo de bloqueo en horas (1 hora)
AXES_LOCKOUT_TEMPLATE = 'registration/login.html'  # Template a mostrar cuando está bloqueado
AXES_LOCKOUT_URL = None  # Usar template en lugar de URL
AXES_RESET_ON_SUCCESS = True  # Resetear contador al hacer login exitoso
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']  # Bloquear por combinación usuario+IP
AXES_VERBOSE = False  # Logging detallado (desactivado para reducir ruido en logs)

# Security Settings para Producción
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True  # Cookies solo por HTTPS
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 año en segundos
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True  # Aplicar a subdominios
    SECURE_HSTS_PRELOAD = True  # Permitir preload en navegadores
    
    # Referrer Policy
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    
    # CSRF Trusted Origins (para PythonAnywhere)
    # Filtrar valores vacíos y asegurar que tengan esquema
    csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    CSRF_TRUSTED_ORIGINS = [
        origin.strip() for origin in csrf_origins 
        if origin.strip() and (origin.strip().startswith('http://') or origin.strip().startswith('https://'))
    ]

# Login/Logout URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# Logging Configuration
def filtrar_informacion_sensible(record):
    """
    Filtro personalizado para evitar que información sensible se registre en logs.
    """
    mensaje = str(record.getMessage()).lower()
    
    # Palabras clave que indican información sensible
    palabras_sensibles = [
        'password', 'passwd', 'pwd', 'pass',
        'token', 'secret', 'key', 'api_key', 'apikey',
        'authorization', 'auth', 'bearer',
        'credit_card', 'cc_number', 'cvv',
        'ssn', 'social_security',
    ]
    
    # Verificar si el mensaje contiene información sensible
    for palabra in palabras_sensibles:
        if palabra in mensaje:
            # Reemplazar información sensible con [REDACTED]
            record.msg = record.msg.replace(palabra, '[REDACTED]')
            # Modificar args si existen
            if record.args:
                record.args = tuple(
                    str(arg).replace(palabra, '[REDACTED]') if isinstance(arg, str) else arg
                    for arg in record.args
                )
    
    return True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'filters': {
        'remove_sensitive': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': filtrar_informacion_sensible,
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django_errors.log',
            'formatter': 'verbose',
            'filters': ['remove_sensitive'],
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['remove_sensitive'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'gestion': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'axes': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',  # Solo mostrar WARNING y ERROR de axes, no INFO
            'propagate': False,
        },
    },
}

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

