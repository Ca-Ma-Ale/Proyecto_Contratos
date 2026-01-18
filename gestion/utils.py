"""
Módulo de utilidades para el sistema de gestión de contratos.
Contiene funciones centralizadas para cálculos uniformes en todo el sistema.
"""

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.contrib import messages


def calcular_fecha_vencimiento(fecha_inicio, meses):
    """
    Calcula fecha de vencimiento usando meses calendario reales.
    Esta función centraliza el cálculo para mantener consistencia en todo el sistema.
    
    Args:
        fecha_inicio: Fecha de inicio de la vigencia
        meses: Número de meses de vigencia
    
    Returns:
        Fecha de vencimiento calculada
    """
    return fecha_inicio + relativedelta(months=meses)


def calcular_meses_vigencia(fecha_inicio, fecha_fin):
    """
    Calcula el número de meses de vigencia entre dos fechas usando el estándar de 30 días por mes.
    
    Args:
        fecha_inicio: Fecha de inicio de la vigencia
        fecha_fin: Fecha de fin de la vigencia
    
    Returns:
        Número de meses de vigencia
    """
    diferencia_dias = (fecha_fin - fecha_inicio).days
    return round(diferencia_dias / 30)


def validar_fecha_vencimiento_poliza(fecha_inicio, fecha_vencimiento, meses_requeridos):
    """
    Valida si una fecha de vencimiento cumple con los meses requeridos.
    
    Args:
        fecha_inicio: Fecha de inicio de la vigencia
        fecha_vencimiento: Fecha de vencimiento a validar
        meses_requeridos: Número de meses requeridos
    
    Returns:
        dict con 'cumple' (bool) y 'observaciones' (list)
    """
    fecha_esperada = calcular_fecha_vencimiento(fecha_inicio, meses_requeridos)
    cumple = fecha_vencimiento >= fecha_esperada
    
    observaciones = []
    if not cumple:
        observaciones.append(
            f"Vigencia insuficiente. Requerida hasta: {fecha_esperada.strftime('%Y-%m-%d')}, "
            f"Actual: {fecha_vencimiento.strftime('%Y-%m-%d')}"
        )
    
    return {
        'cumple': cumple,
        'observaciones': observaciones
    }


def agregar_errores_formulario_a_mensajes(request, form, prefijo_emoji=''):
    """
    Agrega los errores de un formulario Django a los mensajes del sistema.
    
    IMPORTANTE: Esta función centraliza el manejo de errores para asegurar que
    NUNCA se muestre '__all__:' en los mensajes de error. Debe usarse en todas
    las vistas que procesen errores de formulario.
    
    Args:
        request: Objeto request de Django
        form: Instancia del formulario con errores (debe tener form.errors)
        prefijo_emoji: Opcional, emoji o prefijo a agregar (ej: '❌ ')
    
    Ejemplo:
        if not form.is_valid():
            agregar_errores_formulario_a_mensajes(request, form)
            # O con prefijo:
            agregar_errores_formulario_a_mensajes(request, form, prefijo_emoji='❌ ')
    
    Nota:
        - Los errores de campo '__all__' (non_field_errors) se muestran sin
          prefijo del nombre del campo, solo el mensaje de error.
        - Los errores de campos específicos incluyen el nombre del campo.
        - Esta función debe usarse en lugar de bucles manuales que procesen
          form.errors para evitar mostrar '__all__:' al usuario.
    """
    for field, errors in form.errors.items():
        for error in errors:
            if field == '__all__':
                # Errores generales del formulario: solo el mensaje, sin prefijo
                messages.error(request, f'{prefijo_emoji}{str(error)}')
            else:
                # Errores de campos específicos: incluir el nombre del campo
                messages.error(request, f'{prefijo_emoji}{field}: {error}')
