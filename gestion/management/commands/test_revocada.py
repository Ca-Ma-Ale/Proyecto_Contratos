"""
Script de prueba para verificar que se detecta correctamente el status REVOCADA
Ejecutar con: python manage.py test_revocada
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from gestion.models import ClienteLicense
from gestion.license_manager import LicenseManager
import json


class Command(BaseCommand):
    help = 'Prueba la deteccion de status REVOCADA desde Firebase'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== PRUEBA DE DETECCION REVOCADA ===\n'))
        
        # 1. Obtener licencia
        cliente_license = ClienteLicense.objects.filter(is_primary=True).first()
        
        if not cliente_license:
            self.stdout.write(self.style.ERROR('[ERROR] No hay licencia configurada'))
            return
        
        self.stdout.write(f'Clave de licencia: {cliente_license.license_key}')
        self.stdout.write(f'Estado actual en BD: {cliente_license.verification_status}')
        self.stdout.write(f'Activa en BD: {cliente_license.is_active}\n')
        
        # 2. Verificar con Firebase (sin caché)
        self.stdout.write(self.style.WARNING('1. Consultando Firebase (sin caché)...'))
        valida, mensaje, datos = LicenseManager.verificar_licencia_firebase(cliente_license.license_key)
        
        self.stdout.write(f'   Respuesta valida: {valida}')
        self.stdout.write(f'   Mensaje: {mensaje}')
        
        if datos:
            status_firebase = datos.get('status', '')
            self.stdout.write(f'   Status en Firebase: "{status_firebase}"')
            self.stdout.write(f'   isEnabled: {datos.get("isEnabled", True)}')
        
        # 3. Verificar licencia completa (actualiza BD)
        self.stdout.write(self.style.WARNING('\n2. Verificando licencia completa (actualiza BD)...'))
        valida_cliente, mensaje_cliente, datos_cliente = LicenseManager.verificar_licencia_cliente(
            None, 
            forzar_verificacion=False  # Aunque sea False, ahora siempre consulta Firebase
        )
        
        # Recargar desde BD
        cliente_license.refresh_from_db()
        
        self.stdout.write(f'   Verificacion retorno: {valida_cliente}')
        self.stdout.write(f'   Mensaje: {mensaje_cliente}')
        self.stdout.write(f'   Estado en BD DESPUES: {cliente_license.verification_status}')
        self.stdout.write(f'   Activa en BD DESPUES: {cliente_license.is_active}')
        
        # 4. Verificar resultado
        self.stdout.write(self.style.WARNING('\n3. Verificando resultado...'))
        
        if datos:
            status_fb = str(datos.get('status', '')).strip().upper()
            
            if status_fb == 'REVOCADA':
                if not valida:
                    self.stdout.write(self.style.SUCCESS('[OK] verificar_licencia_firebase() detecto REVOCADA correctamente'))
                else:
                    self.stdout.write(self.style.ERROR('[ERROR] verificar_licencia_firebase() NO detecto REVOCADA'))
                
                if cliente_license.verification_status == 'revoked':
                    self.stdout.write(self.style.SUCCESS('[OK] Estado en BD se actualizo a "revoked" correctamente'))
                else:
                    self.stdout.write(self.style.ERROR(f'[ERROR] Estado en BD NO es "revoked", es: {cliente_license.verification_status}'))
                
                if not cliente_license.is_active:
                    self.stdout.write(self.style.SUCCESS('[OK] is_active se actualizo a False correctamente'))
                else:
                    self.stdout.write(self.style.ERROR('[ERROR] is_active NO es False'))
                
                if not valida_cliente:
                    self.stdout.write(self.style.SUCCESS('[OK] verificar_licencia_cliente() retorno False correctamente'))
                else:
                    self.stdout.write(self.style.ERROR('[ERROR] verificar_licencia_cliente() NO retorno False'))
                
                # Resumen
                if (not valida and 
                    cliente_license.verification_status == 'revoked' and 
                    not cliente_license.is_active and 
                    not valida_cliente):
                    self.stdout.write(self.style.SUCCESS('\n[OK] TODAS LAS VERIFICACIONES PASARON'))
                    self.stdout.write(self.style.SUCCESS('La deteccion de REVOCADA funciona correctamente'))
                else:
                    self.stdout.write(self.style.ERROR('\n[ERROR] ALGUNAS VERIFICACIONES FALLARON'))
            else:
                self.stdout.write(self.style.WARNING(f'[INFO] Status en Firebase es "{status_fb}", no es REVOCADA'))
                self.stdout.write(self.style.WARNING('Para probar, cambia el status a "REVOCADA" en Firebase'))
        else:
            self.stdout.write(self.style.ERROR('[ERROR] No se recibieron datos de Firebase'))
        
        self.stdout.write('\n')

