"""
Vista de login personalizada
"""

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def login_with_license(request):
    """
    Vista de login (sin verificación de licencia).
    """
    if request.user.is_authenticated:
        return redirect('gestion:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        raw_next = request.POST.get('next', '') or request.GET.get('next', '')
        if url_has_allowed_host_and_scheme(
            url=raw_next,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = raw_next
        else:
            next_url = reverse('gestion:dashboard')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Bienvenido, {user.get_full_name() or user.username}')
            return redirect(next_url)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')

    raw_next_get = request.GET.get('next', '')
    safe_next = raw_next_get if url_has_allowed_host_and_scheme(
        url=raw_next_get,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ) else reverse('gestion:dashboard')

    return render(request, 'registration/login.html', {'next': safe_next})
