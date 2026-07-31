"""
WSGI config for contratos project.
"""

import os

from django.core.wsgi import get_wsgi_application

if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'contratos.settings'

application = get_wsgi_application()
