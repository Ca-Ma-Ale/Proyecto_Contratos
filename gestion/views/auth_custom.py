"""
Vista de login personalizada con verificación de licencia
"""

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from gestion.license_manager import LicenseManager


def login_with_license(request):
    """
    Vista de login personalizada que verifica la licencia del cliente
    """
    if request.user.is_authenticated:
        return redirect('gestion:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', reverse('gestion:dashboard'))
        
        # Autenticar usuario
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Verificar licencia ANTES de hacer login - FORZAR verificación con Firebase
            valida, mensaje, datos = LicenseManager.verificar_licencia_cliente(user, forzar_verificacion=True)
            
            # Obtener estado de la licencia
            from gestion.models import ClienteLicense
            cliente_license = ClienteLicense.objects.filter(is_primary=True).first()
            
            if cliente_license and cliente_license.verification_status == 'revoked':
                # Si la licencia está revocada, NO permitir login
                messages.error(
                    request, 
                    'La licencia de la organización ha sido revocada o cancelada. '
                    'Por favor, contacte al administrador para más información.'
                )
                return render(request, 'registration/login.html', {
                    'next': request.GET.get('next', reverse('gestion:dashboard'))
                })
            
            # Si la licencia es válida o solo está expirada/inválida (pero no revocada), permitir login
            login(request, user)
            
            if valida:
                # Licencia válida - limpiar alertas de sesión
                if 'license_blocked' in request.session:
                    del request.session['license_blocked']
                if 'license_alert_message' in request.session:
                    del request.session['license_alert_message']
                if 'license_status' in request.session:
                    del request.session['license_status']
                
                messages.success(request, f'Bienvenido, {user.get_full_name() or user.username}')
                return redirect(next_url)
            else:
                # Licencia inválida, expirada (pero no revocada) o deshabilitada
                # Guardar estado de licencia en la sesión para mostrar alerta
                try:
                    if cliente_license:
                        estado = cliente_license.verification_status
                        estado_detallado = cliente_license.obtener_estado_detallado()
                        
                        # Guardar información de la licencia en la sesión
                        request.session['license_status'] = estado
                        request.session['license_message'] = mensaje
                        request.session['license_expired'] = cliente_license.is_expired()
                        request.session['license_dias_vencimiento'] = estado_detallado.get('dias_vencimiento')
                        
                        if estado == 'expired' or cliente_license.is_expired():
                            fecha_exp = cliente_license.expiration_date.strftime("%d/%m/%Y") if cliente_license.expiration_date else "N/A"
                            dias = estado_detallado.get('dias_vencimiento')
                            if dias is not None and dias < 0:
                                request.session['license_alert'] = (
                                    f'La licencia de la organización expiró el {fecha_exp} (hace {abs(dias)} día(s)). '
                                    'Por favor, contacte al administrador para renovar la licencia.'
                                )
                            else:
                                request.session['license_alert'] = (
                                    f'La licencia de la organización expiró el {fecha_exp}. '
                                    'Por favor, contacte al administrador para renovar la licencia.'
                                )
                        elif estado == 'invalid':
                            request.session['license_alert'] = (
                                'La licencia de la organización es inválida. '
                                'Por favor, contacte al administrador.'
                            )
                        else:
                            request.session['license_alert'] = (
                                f'{mensaje}. '
                                'Por favor, contacte al administrador para renovar la licencia.'
                            )
                    else:
                        request.session['license_alert'] = (
                            'No hay licencia configurada para la organización. '
                            'Por favor, contacte al administrador.'
                        )
                        request.session['license_status'] = 'none'
                except:
                    request.session['license_alert'] = (
                        f'{mensaje}. '
                        'Por favor, contacte al administrador para renovar la licencia.'
                    )
                    request.session['license_status'] = 'invalid'
                
                # Redirigir al dashboard donde se mostrará la alerta
                return redirect('gestion:dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    
    return render(request, 'registration/login.html', {
        'next': request.GET.get('next', reverse('gestion:dashboard'))
    })

