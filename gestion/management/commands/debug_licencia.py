"""
Script de depuración para ver exactamente qué devuelve Firebase
Ejecutar con: python manage.py debug_licencia
"""

from django.core.management.base import BaseCommand
from gestion.models import ClienteLicense
from gestion.license_manager import LicenseManager
import json


class Command(BaseCommand):
    help = 'Depura la respuesta de Firebase para ver el status exacto'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== DEPURACION DE RESPUESTA FIREBASE ===\n'))
        
        cliente_license = ClienteLicense.objects.filter(is_primary=True).first()
        
        if not cliente_license:
            self.stdout.write(self.style.ERROR('No hay licencia configurada'))
            return
        
        self.stdout.write(f'Clave de licencia: {cliente_license.license_key}\n')
        
        # Llamar directamente a la función de Firebase
        valida, mensaje, datos = LicenseManager.verificar_licencia_firebase(cliente_license.license_key)
        
        self.stdout.write(f'Respuesta válida: {valida}')
        self.stdout.write(f'Mensaje: {mensaje}\n')
        
        if datos:
            self.stdout.write(self.style.SUCCESS('=== DATOS RECIBIDOS DE FIREBASE ==='))
            self.stdout.write(json.dumps(datos, indent=2, default=str, ensure_ascii=False))
            self.stdout.write('\n')
            
            # Analizar el status
            status_raw = datos.get('status', '')
            status_upper = str(status_raw).strip().upper() if status_raw else ''
            
            self.stdout.write(self.style.WARNING('=== ANALISIS DEL STATUS ==='))
            self.stdout.write(f'Status RAW (original): "{status_raw}"')
            self.stdout.write(f'Status RAW tipo: {type(status_raw)}')
            self.stdout.write(f'Status procesado (upper): "{status_upper}"')
            self.stdout.write(f'Status es None?: {status_raw is None}')
            self.stdout.write(f'Status es vacío?: {status_raw == ""}')
            self.stdout.write(f'Status en lista REVOCADA?: {status_upper in ["REVOCADA", "REVOKED", "CANCELADA", "CANCELLED", "REVOCADO", "CANCELADO"]}')
            
            # Verificar isEnabled
            is_enabled = datos.get('isEnabled', True)
            self.stdout.write(f'\nisEnabled: {is_enabled}')
            self.stdout.write(f'isEnabled tipo: {type(is_enabled)}')
            
            # Verificar si debería estar bloqueada
            if status_upper in ['REVOCADA', 'REVOKED', 'CANCELADA', 'CANCELLED', 'REVOCADO', 'CANCELADO']:
                self.stdout.write(self.style.ERROR('\n[DEBERIA ESTAR BLOQUEADA] Status indica REVOCADA'))
            elif not is_enabled:
                self.stdout.write(self.style.ERROR('\n[DEBERIA ESTAR BLOQUEADA] isEnabled es False'))
            else:
                self.stdout.write(self.style.SUCCESS('\n[NO DEBERIA ESTAR BLOQUEADA] Status no indica revocación'))
        else:
            self.stdout.write(self.style.ERROR('No se recibieron datos de Firebase'))
        
        self.stdout.write('\n')

