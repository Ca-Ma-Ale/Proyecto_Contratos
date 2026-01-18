"""
Decoradores personalizados para el sistema de gestión
"""
from functools import wraps
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages


def login_required_custom(function):
    """
    Decorador personalizado que requiere login y muestra mensaje amigable.
    Maneja el parámetro 'next' para redirigir a la URL original después del login.
    """
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Debe iniciar sesión para acceder a esta página.')
            # Construir URL de login con parámetro 'next' para redirigir después
            login_url = '/login/'
            next_url = request.get_full_path()
            if next_url != login_url:
                return redirect(f'{login_url}?{urlencode({"next": next_url})}')
            return redirect(login_url)
        return function(request, *args, **kwargs)
    return wrap


def admin_required(function):
    """
    Decorador que requiere que el usuario sea staff/admin.
    Maneja el parámetro 'next' para redirigir a la URL original después del login.
    """
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Debe iniciar sesión para acceder a esta página.')
            # Construir URL de login con parámetro 'next' para redirigir después
            login_url = '/login/'
            next_url = request.get_full_path()
            if next_url != login_url:
                return redirect(f'{login_url}?{urlencode({"next": next_url})}')
            return redirect(login_url)
        if not request.user.is_staff:
            messages.error(request, 'No tiene permisos suficientes para acceder a esta página.')
            return redirect('gestion:dashboard')
        return function(request, *args, **kwargs)
    return wrap


def license_required(function):
    """
    Decorador que requiere que la licencia esté activa y vigente.
    Solo permite acceso si la licencia está en estado 'valid', activa y no expirada.
    """
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Debe iniciar sesión para acceder a esta página.')
            login_url = '/login/'
            next_url = request.get_full_path()
            if next_url != login_url:
                return redirect(f'{login_url}?{urlencode({"next": next_url})}')
            return redirect(login_url)
        
        # Verificar licencia
        try:
            from gestion.models import ClienteLicense
            
            cliente_license = ClienteLicense.objects.filter(is_primary=True).first()
            
            if not cliente_license:
                messages.error(request, 'No hay licencia configurada para la organización.')
                return redirect('gestion:dashboard')
            
            cliente_license.refresh_from_db()
            
            # Verificar que la licencia esté activa, vigente y no expirada
            is_valid = (
                cliente_license.is_active and
                cliente_license.verification_status == 'valid' and
                not cliente_license.is_expired()
            )
            
            if not is_valid:
                messages.error(request, 'Su licencia no está activa o ha expirado. Por favor, contacte al administrador.')
                return redirect('gestion:dashboard')
            
            return function(request, *args, **kwargs)
            
        except Exception as e:
            messages.error(request, 'Error verificando la licencia. Por favor, contacte al administrador.')
            return redirect('gestion:dashboard')
    
    return wrap

