"""
Context processors para hacer disponible información global en todos los templates
"""

def empresa_config(request):
    """
    Agrega la configuración de la empresa al contexto de todos los templates
    """
    try:
        from gestion.views.utils import obtener_configuracion_empresa
        configuracion_empresa = obtener_configuracion_empresa()
        return {
            'empresa_config': configuracion_empresa,
        }
    except:
        return {
            'empresa_config': None,
        }


def license_status(request):
    """
    Agrega el estado de la licencia del usuario al contexto de todos los templates
    """
    license_status_data = None
    license_blocked = request.session.get('license_blocked', False)
    license_alert_message = request.session.get('license_alert_message', None)
    
    if request.user.is_authenticated:
        try:
            from gestion.models import ClienteLicense
            from django.utils import timezone
            
            # Obtener la licencia principal de la organización (compartida por todos)
            cliente_license = ClienteLicense.objects.filter(is_primary=True).first()
            
            if not cliente_license:
                return {
                    'license_status': None,
                    'license_blocked': license_blocked,
                    'license_alert_message': license_alert_message,
                }
            
            # Obtener estado detallado de la licencia
            estado_detallado = cliente_license.obtener_estado_detallado()
            dias_restantes = estado_detallado.get('dias_vencimiento')
            
            # Verificar estado de la licencia
            if cliente_license.verification_status == 'revoked':
                license_status_data = {
                    'status': 'revoked', 
                    'icon': 'fa-ban', 
                    'color': 'danger',
                    'text': 'Licencia Revocada',
                    'mensaje': estado_detallado.get('mensaje', 'Licencia revocada o cancelada'),
                    'dias_restantes': None
                }
            elif cliente_license.verification_status == 'expired' or cliente_license.is_expired():
                mensaje = estado_detallado.get('mensaje', 'Licencia expirada')
                if dias_restantes is not None and dias_restantes < 0:
                    mensaje = f'Licencia expirada hace {abs(dias_restantes)} día(s)'
                license_status_data = {
                    'status': 'expired', 
                    'icon': 'fa-exclamation-triangle', 
                    'color': 'danger',
                    'text': 'Licencia Expirada',
                    'mensaje': mensaje,
                    'dias_restantes': dias_restantes
                }
            elif cliente_license.verification_status == 'invalid':
                license_status_data = {
                    'status': 'invalid', 
                    'icon': 'fa-times-circle', 
                    'color': 'danger',
                    'text': 'Licencia Inválida',
                    'mensaje': estado_detallado.get('mensaje', 'Licencia inválida'),
                    'dias_restantes': None
                }
            elif cliente_license.verification_status == 'valid':
                if dias_restantes is not None and dias_restantes <= 30:
                    license_status_data = {
                        'status': 'warning', 
                        'icon': 'fa-exclamation-circle', 
                        'color': 'warning',
                        'text': f'Licencia por Vencer ({dias_restantes} días)',
                        'mensaje': estado_detallado.get('mensaje', f'Vence en {dias_restantes} día(s)'),
                        'dias_restantes': dias_restantes
                    }
                else:
                    mensaje_texto = estado_detallado.get('mensaje', 'Licencia vigente')
                    if dias_restantes is not None:
                        mensaje_texto = f'Licencia vigente - Vence en {dias_restantes} día(s)'
                    license_status_data = {
                        'status': 'valid', 
                        'icon': 'fa-check-circle', 
                        'color': 'success',
                        'text': 'Licencia Válida',
                        'mensaje': mensaje_texto,
                        'dias_restantes': dias_restantes
                    }
            else:
                license_status_data = {
                    'status': cliente_license.verification_status, 
                    'icon': 'fa-clock', 
                    'color': 'info',
                    'text': 'Verificación Pendiente',
                    'mensaje': estado_detallado.get('mensaje', 'Verificación pendiente'),
                    'dias_restantes': dias_restantes
                }
            
            # Agregar información adicional
            if license_status_data:
                license_status_data['expiration_date'] = cliente_license.expiration_date
                license_status_data['license_key'] = cliente_license.license_key
                license_status_data['customer_name'] = cliente_license.customer_name
                license_status_data['customer_email'] = cliente_license.customer_email
                license_status_data['esta_vigente'] = estado_detallado.get('vigente', False)
                license_status_data['estado_detallado'] = estado_detallado
                
        except:
            pass
    
    return {
        'license_status': license_status_data,
        'license_blocked': license_blocked,
        'license_alert_message': license_alert_message,
    }

