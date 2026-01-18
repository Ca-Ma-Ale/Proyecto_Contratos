"""
WSGI config for contratos project.
"""

import os

from django.core.wsgi import get_wsgi_application

# Usar settings_production.py en producción, settings.py en desarrollo
# PythonAnywhere establece DJANGO_SETTINGS_MODULE automáticamente
# Si no está configurado, usar settings_production.py por defecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratos.settings_production')

application = get_wsgi_application()
