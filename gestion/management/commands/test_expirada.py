"""
Script de prueba para verificar que se detecta correctamente cuando la licencia está expirada
Ejecutar con: python manage.py test_expirada
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from gestion.models import ClienteLicense
from gestion.license_manager import LicenseManager
from datetime import datetime, timedelta
import json


class Command(BaseCommand):
    help = 'Prueba la deteccion de licencias expiradas desde Firebase'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== PRUEBA DE DETECCION EXPIRADA ===\n'))
        
        # 1. Obtener licencia
        cliente_license = ClienteLicense.objects.filter(is_primary=True).first()
        
        if not cliente_license:
            self.stdout.write(self.style.ERROR('[ERROR] No hay licencia configurada'))
            return
        
        self.stdout.write(f'Clave de licencia: {cliente_license.license_key}')
        self.stdout.write(f'Estado actual en BD: {cliente_license.verification_status}')
        self.stdout.write(f'Activa en BD: {cliente_license.is_active}')
        self.stdout.write(f'Fecha expiracion en BD: {cliente_license.expiration_date}')
        if cliente_license.expiration_date:
            ahora = timezone.now()
            dias = cliente_license.dias_para_vencimiento()
            self.stdout.write(f'Dias para vencimiento: {dias}')
            self.stdout.write(f'Esta expirada (is_expired): {cliente_license.is_expired()}\n')
        else:
            self.stdout.write('No hay fecha de expiracion configurada\n')
        
        # 2. Verificar con Firebase (sin caché)
        self.stdout.write(self.style.WARNING('1. Consultando Firebase (sin caché)...'))
        valida, mensaje, datos = LicenseManager.verificar_licencia_firebase(cliente_license.license_key)
        
        self.stdout.write(f'   Respuesta valida: {valida}')
        self.stdout.write(f'   Mensaje: {mensaje}')
        
        if datos:
            status_firebase = datos.get('status', '')
            expiration_date = datos.get('expirationDate', '')
            self.stdout.write(f'   Status en Firebase: "{status_firebase}"')
            self.stdout.write(f'   expirationDate en Firebase: {expiration_date}')
            self.stdout.write(f'   isEnabled: {datos.get("isEnabled", True)}')
            
            # Parsear fecha de expiración de Firebase
            if expiration_date:
                try:
                    if isinstance(expiration_date, dict) and '_seconds' in expiration_date:
                        fecha_firebase = timezone.make_aware(
                            datetime.fromtimestamp(expiration_date['_seconds'])
                        )
                        self.stdout.write(f'   Fecha parseada de Firebase: {fecha_firebase}')
                        ahora = timezone.now()
                        if fecha_firebase < ahora:
                            dias_vencida = (ahora - fecha_firebase).days
                            self.stdout.write(self.style.ERROR(f'   [EXPIRADA] La fecha de Firebase es anterior a ahora ({dias_vencida} dias)'))
                        else:
                            dias_restantes = (fecha_firebase - ahora).days
                            self.stdout.write(self.style.SUCCESS(f'   [VIGENTE] La fecha de Firebase es posterior a ahora ({dias_restantes} dias restantes)'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   Error parseando fecha: {e}'))
        
        # 3. Verificar licencia completa (actualiza BD)
        self.stdout.write(self.style.WARNING('\n2. Verificando licencia completa (actualiza BD)...'))
        valida_cliente, mensaje_cliente, datos_cliente = LicenseManager.verificar_licencia_cliente(
            None, 
            forzar_verificacion=False
        )
        
        # Recargar desde BD
        cliente_license.refresh_from_db()
        
        self.stdout.write(f'   Verificacion retorno: {valida_cliente}')
        self.stdout.write(f'   Mensaje: {mensaje_cliente}')
        self.stdout.write(f'   Estado en BD DESPUES: {cliente_license.verification_status}')
        self.stdout.write(f'   Activa en BD DESPUES: {cliente_license.is_active}')
        self.stdout.write(f'   Fecha expiracion en BD DESPUES: {cliente_license.expiration_date}')
        if cliente_license.expiration_date:
            ahora = timezone.now()
            dias = cliente_license.dias_para_vencimiento()
            self.stdout.write(f'   Dias para vencimiento DESPUES: {dias}')
            self.stdout.write(f'   Esta expirada (is_expired) DESPUES: {cliente_license.is_expired()}')
        
        # 4. Verificar resultado
        self.stdout.write(self.style.WARNING('\n3. Verificando resultado...'))
        
        ahora = timezone.now()
        expirada_por_fecha = False
        expirada_por_status = False
        
        if datos:
            status_fb = str(datos.get('status', '')).strip().upper()
            expiration_date = datos.get('expirationDate', '')
            
            # Verificar si está expirada por fecha
            if expiration_date:
                try:
                    if isinstance(expiration_date, dict) and '_seconds' in expiration_date:
                        fecha_firebase = timezone.make_aware(
                            datetime.fromtimestamp(expiration_date['_seconds'])
                        )
                        if fecha_firebase < ahora:
                            expirada_por_fecha = True
                            self.stdout.write(self.style.ERROR('[EXPIRADA POR FECHA] La fecha de Firebase es anterior a ahora'))
                        else:
                            self.stdout.write(self.style.SUCCESS('[VIGENTE POR FECHA] La fecha de Firebase es posterior a ahora'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error parseando fecha: {e}'))
            
            # Verificar si está expirada por status
            if status_fb in ['EXPIRADA', 'EXPIRED']:
                expirada_por_status = True
                self.stdout.write(self.style.ERROR(f'[EXPIRADA POR STATUS] Status en Firebase es: "{status_fb}"'))
            else:
                self.stdout.write(self.style.SUCCESS(f'[NO EXPIRADA POR STATUS] Status en Firebase es: "{status_fb}"'))
            
            # Verificar si debería estar bloqueada
            if expirada_por_fecha or expirada_por_status:
                if not valida:
                    self.stdout.write(self.style.SUCCESS('[OK] verificar_licencia_firebase() detecto EXPIRADA correctamente'))
                else:
                    self.stdout.write(self.style.ERROR('[ERROR] verificar_licencia_firebase() NO detecto EXPIRADA'))
                
                if cliente_license.verification_status == 'expired':
                    self.stdout.write(self.style.SUCCESS('[OK] Estado en BD se actualizo a "expired" correctamente'))
                else:
                    self.stdout.write(self.style.ERROR(f'[ERROR] Estado en BD NO es "expired", es: {cliente_license.verification_status}'))
                
                if not cliente_license.is_active:
                    self.stdout.write(self.style.SUCCESS('[OK] is_active se actualizo a False correctamente'))
                else:
                    self.stdout.write(self.style.ERROR('[ERROR] is_active NO es False'))
                
                if not valida_cliente:
                    self.stdout.write(self.style.SUCCESS('[OK] verificar_licencia_cliente() retorno False correctamente'))
                else:
                    self.stdout.write(self.style.ERROR('[ERROR] verificar_licencia_cliente() NO retorno False'))
                
                # Verificar is_expired()
                if cliente_license.is_expired():
                    self.stdout.write(self.style.SUCCESS('[OK] is_expired() retorna True correctamente'))
                else:
                    self.stdout.write(self.style.ERROR('[ERROR] is_expired() NO retorna True'))
                
                # Resumen
                if (not valida and 
                    cliente_license.verification_status == 'expired' and 
                    not cliente_license.is_active and 
                    not valida_cliente and
                    cliente_license.is_expired()):
                    self.stdout.write(self.style.SUCCESS('\n[OK] TODAS LAS VERIFICACIONES PASARON'))
                    self.stdout.write(self.style.SUCCESS('La deteccion de EXPIRADA funciona correctamente'))
                else:
                    self.stdout.write(self.style.ERROR('\n[ERROR] ALGUNAS VERIFICACIONES FALLARON'))
            else:
                self.stdout.write(self.style.WARNING('[INFO] La licencia NO esta expirada'))
                self.stdout.write(self.style.WARNING('Para probar, cambia la fecha de expiracion a una fecha pasada en Firebase'))
        else:
            self.stdout.write(self.style.ERROR('[ERROR] No se recibieron datos de Firebase'))
        
        self.stdout.write('\n')

