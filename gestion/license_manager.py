"""
Módulo de gestión de licencias adaptado para Django
Validación de licencia por cliente al iniciar sesión
"""

import requests
from datetime import datetime
from django.utils import timezone
from django.contrib.auth.models import User

# URL de la Cloud Function de Firebase
URL_FUNCION_FIREBASE = "https://us-central1-app-contable-licencias.cloudfunctions.net/activateLicense"


class LicenseManager:
    """
    Gestiona la validación de licencias por cliente usando Firebase
    """
    
    @staticmethod
    def verificar_licencia_firebase(clave_licencia):
        """
        Verifica el estado de una licencia en Firebase
        
        Args:
            clave_licencia: Clave de licencia
            
        Returns:
            tuple: (valida: bool, mensaje: str, datos: dict)
        """
        # Generar un fingerprint básico del servidor (sin hardware específico)
        import hashlib
        import platform
        server_id = f"SGC-{platform.node()}-{platform.system()}"
        fingerprint = hashlib.sha256(server_id.encode()).hexdigest()
        
        payload = {
            "key": clave_licencia,
            "fingerprint": fingerprint,
            "softwareVersion": "1.0"
        }
        
        try:
            headers = {
                'User-Agent': 'SistemaGestionContratos/1.0',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
            }
            
            respuesta = requests.post(
                URL_FUNCION_FIREBASE,
                json=payload,
                headers=headers,
                timeout=25,
                verify=True
            )
            
            if 200 <= respuesta.status_code < 300:
                resultado_json = respuesta.json()
                mensaje_servidor = resultado_json.get('message', "Verificación exitosa")
                
                # Procesar datos de licencia
                datos_licencia = {}
                
                if 'licenseData' in resultado_json:
                    license_data = resultado_json['licenseData']
                    # Obtener status y convertir a mayúsculas para comparación
                    status_firebase = str(license_data.get('status', '')).strip().upper()
                    is_enabled = license_data.get('isEnabled', True)
                    
                    datos_licencia = {
                        'expirationDate': license_data.get('expirationDate'),
                        'customerName': license_data.get('customerName', ''),
                        'customerEmail': license_data.get('customerEmail', ''),
                        'licenseType': license_data.get('licenseType', ''),
                        'activationStatus': license_data.get('activationStatus', ''),
                        'softwareVersion': license_data.get('softwareVersion', ''),
                        'status': license_data.get('status', ''),
                        'isEnabled': is_enabled,
                    }
                    
                    # Verificar si la licencia está revocada o deshabilitada ANTES de retornar True
                    # Verificar múltiples variantes del status revocado
                    if status_firebase in ['REVOCADA', 'REVOKED', 'CANCELADA', 'CANCELLED', 'REVOCADO', 'CANCELADO']:
                        return False, "Licencia revocada o cancelada", datos_licencia
                    
                    if not is_enabled:
                        return False, "Licencia deshabilitada", datos_licencia
                else:
                    # Si no hay licenseData, considerar como error
                    return False, "No se recibieron datos de licencia desde Firebase", None
                
                return True, mensaje_servidor, datos_licencia
            else:
                mensaje_error = f"Error del servidor ({respuesta.status_code})"
                try:
                    error_response = respuesta.json()
                    if 'error' in error_response:
                        error_details = error_response.get('error', {})
                        mensaje_error = error_details.get('message', mensaje_error)
                    else:
                        mensaje_error = error_response.get('message', mensaje_error)
                except:
                    mensaje_error = f"Error del servidor ({respuesta.status_code}): {respuesta.text[:200]}"
                return False, mensaje_error, None
                
        except requests.exceptions.RequestException as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Error de conexión al verificar licencia con Firebase", exc_info=True)
            return False, "Error de conexión al verificar licencia", None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Error inesperado al verificar licencia", exc_info=True)
            return False, "Error inesperado al verificar licencia", None
    
    @staticmethod
    def verificar_licencia_cliente(usuario, forzar_verificacion=False):
        """
        Verifica la licencia global de la organización
        Una única licencia es compartida por todos los usuarios
        
        En cada inicio de sesión (forzar_verificacion=True), actualiza TODOS los datos
        de la licencia desde Firebase y recalcula el estado basado en la fecha actual.
        
        Args:
            usuario: Instancia de User de Django (no se usa, pero se mantiene para compatibilidad)
            forzar_verificacion: Si True, siempre consulta Firebase y actualiza todos los datos (útil en login)
            
        Returns:
            tuple: (valida: bool, mensaje: str, datos: dict)
        """
        from gestion.models import ClienteLicense
        
        try:
            # Obtener la licencia principal de la organización (compartida por todos)
            cliente_license = ClienteLicense.objects.filter(is_primary=True).first()
            
            if not cliente_license:
                return False, "No hay licencia configurada para la organización", None
            
            # SIEMPRE verificar con Firebase para detectar cambios inmediatamente (especialmente REVOCADA)
            # Se eliminó el uso de caché para garantizar que siempre se consulte Firebase
            valida, mensaje, datos = LicenseManager.verificar_licencia_firebase(cliente_license.license_key)
            
            # Si Firebase devuelve error 403 o mensaje de expiración, marcar como expirada
            if not valida and not datos:
                mensaje_lower = mensaje.lower() if mensaje else ''
                if 'expirado' in mensaje_lower or 'expired' in mensaje_lower or '403' in str(mensaje):
                    # Firebase indica que está expirada, marcar como expirada inmediatamente
                    cliente_license.verification_status = 'expired'
                    cliente_license.is_active = False
                    cliente_license.last_verification = timezone.now()
                    cliente_license.save()
                    
                    # Calcular días vencida si hay fecha de expiración
                    if cliente_license.expiration_date:
                        dias_vencida = cliente_license.dias_para_vencimiento()
                        if dias_vencida is not None and dias_vencida < 0:
                            return False, f"Licencia expirada hace {abs(dias_vencida)} día(s)", None
                    
                    return False, "Licencia expirada", None
            
            # ACTUALIZAR TODOS LOS DATOS desde Firebase (en cada inicio de sesión)
            if datos:
                # Actualizar información básica del cliente
                cliente_license.customer_name = datos.get('customerName', cliente_license.customer_name or '')
                cliente_license.customer_email = datos.get('customerEmail', cliente_license.customer_email or '')
                
                # Parsear y actualizar fecha de expiración desde Firebase
                if datos.get('expirationDate'):
                    try:
                        exp_date = datos.get('expirationDate')
                        if isinstance(exp_date, dict) and '_seconds' in exp_date:
                            nueva_fecha = timezone.make_aware(
                                datetime.fromtimestamp(exp_date['_seconds'])
                            )
                            cliente_license.expiration_date = nueva_fecha
                        elif isinstance(exp_date, (int, float)):
                            nueva_fecha = timezone.make_aware(
                                datetime.fromtimestamp(exp_date)
                            )
                            cliente_license.expiration_date = nueva_fecha
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Error parseando fecha de expiración: {e}")
                
                # Obtener status y estado de habilitación desde Firebase
                status_firebase = str(datos.get('status', '')).strip().upper()
                is_enabled = datos.get('isEnabled', True)
                
                # Determinar estado basado en status de Firebase y fecha actual
                ahora = timezone.now()
                
                # Si está revocada o deshabilitada en Firebase, marcar como revocada
                if status_firebase in ['REVOCADA', 'REVOKED', 'CANCELADA', 'CANCELLED', 'REVOCADO', 'CANCELADO'] or not is_enabled:
                    cliente_license.verification_status = 'revoked'
                    cliente_license.is_active = False
                else:
                    # Verificar vencimiento comparando fecha actual con fecha de expiración
                    if cliente_license.expiration_date:
                        if ahora > cliente_license.expiration_date:
                            # La fecha actual es mayor que la de expiración = EXPIRADA
                            cliente_license.verification_status = 'expired'
                            cliente_license.is_active = False
                        else:
                            # La fecha actual es menor o igual = VIGENTE (si el status de Firebase lo permite)
                            if status_firebase in ['ACTIVA', 'ACTIVE']:
                                cliente_license.verification_status = 'valid'
                                cliente_license.is_active = True
                            elif status_firebase in ['EXPIRADA', 'EXPIRED']:
                                cliente_license.verification_status = 'expired'
                                cliente_license.is_active = False
                            else:
                                # Si no hay status explícito, asumir válida si no está expirada
                                cliente_license.verification_status = 'valid'
                                cliente_license.is_active = True
                    else:
                        # No hay fecha de expiración
                        if status_firebase in ['ACTIVA', 'ACTIVE']:
                            cliente_license.verification_status = 'valid'
                            cliente_license.is_active = True
                        else:
                            cliente_license.verification_status = 'invalid'
                            cliente_license.is_active = False
            elif not valida:
                # Si no hay datos y la verificación falló, marcar como inválida
                cliente_license.verification_status = 'invalid'
                cliente_license.is_active = False
            
            # Actualizar última verificación
            cliente_license.last_verification = timezone.now()
            
            # Guardar TODOS los cambios
            cliente_license.save()
            
            # Recargar desde BD para asegurar que tenemos todos los datos actualizados
            cliente_license.refresh_from_db()
            
            # Verificaciones finales antes de permitir acceso (usando datos actualizados)
            if cliente_license.verification_status == 'revoked':
                return False, "Licencia revocada o cancelada", datos
            
            # Verificar expiración usando la fecha actualizada desde Firebase
            if cliente_license.is_expired():
                cliente_license.verification_status = 'expired'
                cliente_license.is_active = False
                cliente_license.save()
                dias_vencida = cliente_license.dias_para_vencimiento()
                if dias_vencida is not None and dias_vencida < 0:
                    return False, f"Licencia expirada hace {abs(dias_vencida)} día(s)", datos
                return False, "Licencia expirada", datos
            
            if cliente_license.verification_status == 'expired':
                return False, "Licencia expirada", datos
            
            if not cliente_license.is_active:
                return False, "Licencia inactiva", datos
            
            # Si llegamos aquí, la licencia es válida
            # Calcular días para vencimiento para el mensaje
            dias = cliente_license.dias_para_vencimiento()
            if dias is not None:
                if dias <= 30:
                    mensaje = f"Licencia vigente - Vence en {dias} día(s)"
                else:
                    mensaje = f"Licencia vigente - Vence en {dias} día(s)"
            
            return valida, mensaje, datos
            
        except ClienteLicense.DoesNotExist:
            return False, "Usuario no tiene licencia asignada", None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Error verificando licencia", exc_info=True)
            return False, "Error verificando licencia. Por favor, contacte al administrador.", None

