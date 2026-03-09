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


def admin_general_required(function):
    """
    Decorador que requiere que el usuario sea el Admin General del sistema.
    El Admin General se identifica por tener PerfilUsuario.es_admin_general = True.
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
        try:
            es_admin = request.user.perfil.es_admin_general
        except Exception:
            es_admin = False
        if not es_admin:
            messages.error(
                request,
                'Acceso restringido. Esta sección es exclusiva del Admin General.'
            )
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

        from gestion.license_manager import LicenseManager
        is_valid, status, message = LicenseManager.es_licencia_valida()

        if not is_valid:
            messages.error(request, f'Acceso denegado: {message}. Por favor, contacte al administrador.')
            return redirect('gestion:dashboard')

        return function(request, *args, **kwargs)

    return wrap

