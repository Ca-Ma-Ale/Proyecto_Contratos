from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def formato_moneda(value):
    """Formatea un valor monetario con separadores de miles y sin decimales"""
    if value is None:
        return "0"
    
    try:
        # Convertir a entero para quitar decimales
        valor_entero = int(float(value))
        # Formatear con separadores de miles
        return f"{valor_entero:,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"

@register.filter
def formato_porcentaje(value):
    """Formatea un porcentaje sin decimales si es entero"""
    if value is None:
        return "0%"
    
    try:
        valor_num = float(value)
        if valor_num % 1 == 0:
            return f"{int(valor_num)}%"
        else:
            return f"{valor_num}%"
    except (ValueError, TypeError):
        return "0%"

@register.filter
def add_class(field, css_class):
    """Añade una clase CSS a un campo de formulario"""
    if hasattr(field, 'field'):
        widget = field.field.widget
        attrs = widget.attrs.copy()
        if 'class' in attrs:
            attrs['class'] = f"{attrs['class']} {css_class}"
        else:
            attrs['class'] = css_class
        widget.attrs = attrs
    return field


@register.filter
def display_mes_choice(value):
    """Convierte la clave del mes (e.g., 'ENERO') a su nombre en español.

    Se usa cuando en la vista vigente tenemos el valor del `choices` y no el
    método `get_<field>_display()` del modelo.
    """
    if not value:
        return "N/A"
    mapping = {
        'ENERO': 'Enero',
        'FEBRERO': 'Febrero',
        'MARZO': 'Marzo',
        'ABRIL': 'Abril',
        'MAYO': 'Mayo',
        'JUNIO': 'Junio',
        'JULIO': 'Julio',
        'AGOSTO': 'Agosto',
        'SEPTIEMBRE': 'Septiembre',
        'OCTUBRE': 'Octubre',
        'NOVIEMBRE': 'Noviembre',
        'DICIEMBRE': 'Diciembre',
    }
    return mapping.get(str(value).upper(), str(value))


@register.filter
def display_periodicidad_ipc(value):
    """Devuelve etiqueta legible para periodicidad IPC."""
    if not value:
        return "N/A"
    value_upper = str(value).upper()
    if value_upper == 'ANUAL':
        return 'Anual'
    if value_upper == 'FECHA_ESPECIFICA':
        return 'Fecha Específica'
    return str(value)