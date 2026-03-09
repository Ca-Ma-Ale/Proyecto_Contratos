# -*- coding: utf-8 -*-
"""
Comando para forzar licencia válida y limpiar sesiones.
Uso: python manage.py activar_licencia_y_limpiar_sesiones

Requiere SECRET_KEY y DJANGO_SETTINGS_MODULE configurados.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.sessions.models import Session
from datetime import datetime


class Command(BaseCommand):
    help = 'Fuerza la licencia a válida y elimina todas las sesiones (obligando re-login)'

    def handle(self, *args, **options):
        from gestion.models import ClienteLicense

        lic = ClienteLicense.objects.filter(is_primary=True).first()
        if not lic:
            self.stdout.write(self.style.ERROR('No hay licencia configurada.'))
            return

        lic.verification_status = 'valid'
        lic.is_active = True
        if not lic.expiration_date or lic.expiration_date < timezone.now():
            lic.expiration_date = timezone.make_aware(datetime(2027, 1, 16, 23, 59, 59))
        lic.save()

        self.stdout.write(self.style.SUCCESS(f'Licencia actualizada: {lic.license_key} -> valid, active'))

        n, _ = Session.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Sesiones eliminadas: {n}'))

        self.stdout.write('')
        self.stdout.write('Reinicia la aplicación (gunicorn/uwsgi) y pide a los usuarios que inicien sesión de nuevo.')
