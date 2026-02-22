"""
Middleware para verificar licencias en cada request
"""

import time
import logging

from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

# Tiempo de caché de la verificación de licencia en sesión (segundos)
LICENSE_CACHE_TTL = 300  # 5 minutos


class LicenseCheckMiddleware(MiddlewareMixin):
    """
    Middleware que verifica la licencia del usuario en cada request.
    - Usa caché de sesión (5 min) para evitar queries a BD en cada request.
    - Fail-closed: ante cualquier error inesperado, cierra la sesión.
    - Revocada: fuerza logout inmediato sin importar el caché.
    """

    # URLs que no requieren verificación de licencia
    EXEMPT_URLS = [
        '/login/',
        '/login-cliente/',
        '/logout/',
        '/admin/login/',
        '/admin/logout/',
    ]

    def _es_dashboard(self, path):
        return path == '/' or path == '/dashboard/' or path.startswith('/dashboard')

    def _invalidar_cache_licencia(self, session):
        """Elimina las claves de caché de licencia de la sesión."""
        for key in ('license_last_check', 'license_cached_status', 'license_cached_valid'):
            session.pop(key, None)

    def _usar_cache_si_vigente(self, request):
        """
        Retorna True si el caché de sesión es válido y la licencia estaba OK.
        Retorna False si el caché expiró, no existe, o la licencia estaba bloqueada.
        Lanza redirect si el caché indica licencia revocada.
        """
        ultima = request.session.get('license_last_check', 0)
        if time.time() - ultima >= LICENSE_CACHE_TTL:
            return False  # caché expirado

        cached_valid = request.session.get('license_cached_valid')
        cached_status = request.session.get('license_cached_status', '')

        # Si estaba revocada según el caché, forzar logout sin esperar al TTL
        if cached_status == 'revoked':
            messages.error(request, 'Su licencia ha sido revocada. Por favor, contacte al administrador.')
            logout(request)
            self._invalidar_cache_licencia(request.session)
            return 'redirect_login'

        return cached_valid  # True → licencia OK en caché, None/False → bloqueada en caché

    def _actualizar_cache(self, request, is_valid, status):
        """Guarda el estado de la licencia en el caché de sesión."""
        request.session['license_last_check'] = time.time()
        request.session['license_cached_valid'] = is_valid
        request.session['license_cached_status'] = status

    def process_request(self, request):
        # Si el usuario no está autenticado, no verificar licencia
        if not request.user.is_authenticated:
            return None

        # Excluir URLs de login/logout
        if any(request.path.startswith(url) for url in self.EXEMPT_URLS):
            return None

        # --- Comprobar caché de sesión ---
        cache_result = self._usar_cache_si_vigente(request)
        if cache_result == 'redirect_login':
            return redirect('/login/')
        if cache_result is True:
            # Licencia válida según caché → no consultar BD
            return None
        # cache_result is False o None → verificar con BD

        # --- Verificación real contra BD ---
        try:
            from gestion.models import ClienteLicense
            from gestion.license_manager import LicenseManager

            cliente_license = ClienteLicense.objects.filter(is_primary=True).first()

            if not cliente_license:
                messages.error(request, 'No hay licencia configurada para la organización.')
                self._invalidar_cache_licencia(request.session)
                return redirect('gestion:dashboard') if not self._es_dashboard(request.path) else None

            cliente_license.refresh_from_db()

            # Forzar re-verificación con Firebase si está revocada o inactiva
            if cliente_license.verification_status == 'revoked' or not cliente_license.is_active:
                LicenseManager.verificar_licencia_cliente(request.user, forzar_verificacion=True)
                cliente_license.refresh_from_db()

            # Logout inmediato si está revocada
            if cliente_license.verification_status == 'revoked':
                messages.error(request, 'Su licencia ha sido revocada o cancelada. Por favor, contacte al administrador.')
                logout(request)
                self._invalidar_cache_licencia(request.session)
                return redirect('/login/')

            is_valid = (
                cliente_license.is_active and
                cliente_license.verification_status == 'valid' and
                not cliente_license.is_expired()
            )

            # Actualizar caché de sesión con el resultado
            self._actualizar_cache(request, is_valid, cliente_license.verification_status)

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

                # Para el dashboard: mostrar alerta pero permitir acceso
                if self._es_dashboard(request.path):
                    return None
                # Para el resto: bloquear
                messages.error(request, request.session.get('license_alert_message', 'Licencia no válida.'))
                return redirect('gestion:dashboard')
            else:
                # Licencia válida: limpiar alertas previas
                for key in ('license_blocked', 'license_alert_message', 'license_status'):
                    request.session.pop(key, None)

        except Exception:
            logger.error("Error verificando licencia en middleware", exc_info=True)
            # FAIL-CLOSED: ante cualquier error inesperado, cerrar sesión
            messages.error(request, 'Error del sistema al verificar la licencia. Por favor, inicie sesión nuevamente.')
            logout(request)
            self._invalidar_cache_licencia(request.session)
            return redirect('/login/')

        return None

