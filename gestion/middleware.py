"""
Middleware para verificar licencias en cada request
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


class LicenseCheckMiddleware(MiddlewareMixin):
    """
    Middleware que verifica la licencia del usuario en cada request
    Bloquea el acceso si la licencia está expirada, revocada o deshabilitada
    """
    
    # URLs que no requieren verificación de licencia
    EXEMPT_URLS = [
        '/login/',
        '/login-cliente/',
        '/logout/',
        '/admin/login/',
        '/admin/logout/',
    ]
    
    def process_request(self, request):
        # Si el usuario no está autenticado, no verificar licencia
        if not request.user.is_authenticated:
            return None
        
        # Excluir URLs de login/logout y admin (solo para login/logout)
        if any(request.path.startswith(url) for url in self.EXEMPT_URLS):
            return None
        
        # Para el dashboard, verificar licencia pero permitir acceso solo si no está revocada
        # Si está revocada, bloquear completamente
        if request.path == '/' or request.path == '/dashboard/' or request.path.startswith('/dashboard'):
            try:
                from gestion.models import ClienteLicense
                from gestion.license_manager import LicenseManager
                
                cliente_license = ClienteLicense.objects.filter(is_primary=True).first()
                if cliente_license:
                    cliente_license.refresh_from_db()
                    
                    # Si la licencia está marcada como revocada, forzar verificación con Firebase
                    if cliente_license.verification_status == 'revoked' or not cliente_license.is_active:
                        LicenseManager.verificar_licencia_cliente(request.user, forzar_verificacion=True)
                        cliente_license.refresh_from_db()
                    
                    is_valid = (
                        cliente_license.is_active and
                        cliente_license.verification_status == 'valid' and
                        not cliente_license.is_expired()
                    )
                    
                    # Si está revocada, BLOQUEAR acceso completamente
                    if cliente_license.verification_status == 'revoked':
                        messages.error(request, 'Su licencia ha sido revocada o cancelada. Por favor, contacte al administrador.')
                        # Cerrar sesión del usuario
                        from django.contrib.auth import logout
                        logout(request)
                        return redirect('gestion:login')
                    
                    if not is_valid:
                        request.session['license_blocked'] = True
                        if not cliente_license.is_active:
                            request.session['license_alert_message'] = 'Su licencia está inactiva. Por favor, contacte al administrador.'
                        elif cliente_license.verification_status == 'expired' or cliente_license.is_expired():
                            fecha_exp = cliente_license.expiration_date.strftime("%d/%m/%Y") if cliente_license.expiration_date else "N/A"
                            request.session['license_alert_message'] = f'Su licencia expiró el {fecha_exp}. Por favor, contacte al administrador para renovar.'
                        elif cliente_license.verification_status == 'invalid':
                            request.session['license_alert_message'] = 'Su licencia es inválida. Por favor, contacte al administrador.'
                        request.session['license_status'] = cliente_license.verification_status
                    else:
                        if 'license_blocked' in request.session:
                            del request.session['license_blocked']
                        if 'license_alert_message' in request.session:
                            del request.session['license_alert_message']
                        if 'license_status' in request.session:
                            del request.session['license_status']
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error("Error en middleware verificando licencia", exc_info=True)
                messages.error(request, 'Error verificando la licencia. Por favor, contacte al administrador.')
            return None
        
        # Para todas las demás URLs, bloquear si la licencia no está activa y vigente
        try:
            from gestion.models import ClienteLicense
            from gestion.license_manager import LicenseManager
            
            cliente_license = ClienteLicense.objects.filter(is_primary=True).first()
            
            if not cliente_license:
                messages.error(request, 'No hay licencia configurada para la organización.')
                return redirect('gestion:dashboard')
            
            cliente_license.refresh_from_db()
            
            # Si la licencia está marcada como revocada localmente, forzar verificación con Firebase
            # para asegurar que el estado esté actualizado
            if cliente_license.verification_status == 'revoked' or not cliente_license.is_active:
                LicenseManager.verificar_licencia_cliente(request.user, forzar_verificacion=True)
            cliente_license.refresh_from_db()
            
            # Verificar que la licencia esté activa, vigente y no expirada
            is_valid = (
                cliente_license.is_active and
                cliente_license.verification_status == 'valid' and
                not cliente_license.is_expired()
            )
            
            if not is_valid:
                if not cliente_license.is_active:
                    messages.error(request, 'Su licencia está inactiva. Por favor, contacte al administrador.')
                elif cliente_license.verification_status == 'revoked':
                    messages.error(request, 'Su licencia ha sido revocada o cancelada. Por favor, contacte al administrador.')
                elif cliente_license.verification_status == 'expired' or cliente_license.is_expired():
                    fecha_exp = cliente_license.expiration_date.strftime("%d/%m/%Y") if cliente_license.expiration_date else "N/A"
                    messages.error(request, f'Su licencia expiró el {fecha_exp}. Por favor, contacte al administrador para renovar.')
                elif cliente_license.verification_status == 'invalid':
                    messages.error(request, 'Su licencia es inválida. Por favor, contacte al administrador.')
                else:
                    messages.error(request, 'Su licencia no está activa. Por favor, contacte al administrador.')
                return redirect('gestion:dashboard')
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Error verificando licencia en middleware", exc_info=True)
            messages.error(request, 'Error verificando la licencia. Por favor, contacte al administrador.')
            return redirect('gestion:dashboard')
        
        return None

