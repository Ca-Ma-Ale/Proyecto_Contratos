"""
Template tags para mostrar información de licencias
"""

from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()


@register.simple_tag
def get_license_status(user):
    """
    Obtiene el estado de la licencia del usuario
    
    Returns:
        dict con información de la licencia o None
    """
    try:
        from gestion.models import ClienteLicense
        
        cliente_license = ClienteLicense.objects.get(usuario=user)
        
        # Calcular días restantes
        dias_restantes = None
        if cliente_license.expiration_date:
            delta = cliente_license.expiration_date.date() - timezone.now().date()
            dias_restantes = delta.days
        
        # Determinar estado visual
        estado_visual = 'valid'
        icono = 'fa-check-circle'
        color = 'success'
        texto = 'Licencia Válida'
        
        if cliente_license.verification_status == 'expired' or (dias_restantes is not None and dias_restantes < 0):
            estado_visual = 'expired'
            icono = 'fa-exclamation-triangle'
            color = 'danger'
            texto = 'Licencia Expirada'
        elif cliente_license.verification_status == 'invalid':
            estado_visual = 'invalid'
            icono = 'fa-times-circle'
            color = 'danger'
            texto = 'Licencia Inválida'
        elif dias_restantes is not None and dias_restantes <= 30:
            estado_visual = 'warning'
            icono = 'fa-exclamation-circle'
            color = 'warning'
            texto = f'Licencia por Vencer ({dias_restantes} días)'
        elif cliente_license.verification_status == 'pending':
            estado_visual = 'pending'
            icono = 'fa-clock'
            color = 'info'
            texto = 'Verificación Pendiente'
        
        return {
            'status': estado_visual,
            'icon': icono,
            'color': color,
            'text': texto,
            'dias_restantes': dias_restantes,
            'expiration_date': cliente_license.expiration_date,
            'license_key': cliente_license.license_key,
            'customer_name': cliente_license.customer_name,
        }
    except:
        return None


@register.simple_tag
def get_license_status_simple(user):
    """
    Versión simplificada que solo retorna el estado básico
    """
    try:
        from gestion.models import ClienteLicense
        
        cliente_license = ClienteLicense.objects.get(usuario=user)
        
        if cliente_license.is_expired():
            return {'status': 'expired', 'icon': 'fa-exclamation-triangle', 'color': 'danger'}
        
        if cliente_license.verification_status == 'valid':
            dias_restantes = None
            if cliente_license.expiration_date:
                delta = cliente_license.expiration_date.date() - timezone.now().date()
                dias_restantes = delta.days
            
            if dias_restantes is not None and dias_restantes <= 30:
                return {'status': 'warning', 'icon': 'fa-exclamation-circle', 'color': 'warning'}
            return {'status': 'valid', 'icon': 'fa-check-circle', 'color': 'success'}
        
        return {'status': cliente_license.verification_status, 'icon': 'fa-clock', 'color': 'info'}
    except:
        return {'status': 'none', 'icon': 'fa-question-circle', 'color': 'secondary'}

