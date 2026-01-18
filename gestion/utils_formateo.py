"""
Utilidades para formateo y limpieza de datos numéricos en formularios.
Centraliza la lógica de limpieza para evitar duplicación.
"""
import re
from django import forms


def aplicar_nombre_propio(texto):
    """
    Convierte texto a formato nombre propio (primera letra mayúscula, resto minúscula).
    
    Args:
        texto: Texto a convertir
    
    Returns:
        Texto convertido a formato nombre propio
    
    Ejemplos:
        "juan pérez" -> "Juan Pérez"
        "MARÍA GARCÍA" -> "María García"
        "carlos  lópez" -> "Carlos López"
    """
    if not texto or not isinstance(texto, str):
        return texto
    
    texto = texto.strip()
    
    if not texto:
        return texto
    
    palabras = texto.split()
    palabras_formateadas = []
    
    for palabra in palabras:
        if palabra:
            palabra_formateada = palabra[0].upper() + palabra[1:].lower()
            palabras_formateadas.append(palabra_formateada)
    
    return ' '.join(palabras_formateadas)


def es_campo_excluido_nombre_propio(field_name, field):
    """
    Determina si un campo debe ser excluido de la conversión a nombre propio.
    
    Args:
        field_name: Nombre del campo
        field: Instancia del campo del formulario
    
    Returns:
        True si el campo debe ser excluido, False en caso contrario
    """
    campos_excluidos = [
        'email', 'url', 'password', 'username', 'nit', 'telefono', 'celular',
        'numero', 'num_', 'codigo', 'cod_', 'id', 'pk', 'url_archivo',
        'numero_contrato', 'numero_poliza', 'numero_otrosi', 'numero_renovacion',
        'nit_empresa', 'nit_concedente'
    ]
    
    field_name_lower = field_name.lower()
    
    for excluido in campos_excluidos:
        if excluido in field_name_lower:
            return True
    
    if isinstance(field, (forms.EmailField, forms.URLField, forms.IntegerField, 
                         forms.DecimalField, forms.FloatField, forms.DateField,
                         forms.DateTimeField, forms.TimeField)):
        return True
    
    if hasattr(field, 'widget'):
        widget_type = type(field.widget).__name__
        if 'Password' in widget_type or 'Email' in widget_type or 'URL' in widget_type:
            return True
    
    return False


def limpiar_valor_numerico(value, campo_nombre="campo"):
    """
    Función universal para limpiar valores numéricos con formateo.
    
    Args:
        value: Valor a limpiar (puede ser string con formato o número)
        campo_nombre: Nombre del campo para mensajes de error
    
    Returns:
        Valor numérico limpio (float) o None si está vacío
    
    Raises:
        ValueError: Si el valor no puede convertirse a número
    """
    if value is None or value == '':
        return None
        
    if isinstance(value, str):
        # Remover espacios
        value = value.strip()
        
        # Remover símbolos de porcentaje
        if value.endswith('%'):
            value = value[:-1]
        
        # Remover símbolo $
        value = value.replace('$', '')
        
        # Si quedó vacío después de limpiar, retornar None
        if not value:
            return None
        
        # Detectar formato: colombiano (punto para miles, coma para decimales) o inglés (punto para decimales)
        # Si tiene comas, asumir formato colombiano (ej: "6.800.000,50")
        # Si tiene puntos pero NO comas, y tiene más de un punto, asumir formato colombiano (ej: "6.800.000")
        # Si tiene un solo punto y no tiene comas, podría ser formato inglés (ej: "6800000.00")
        
        tiene_comas = ',' in value
        puntos = value.count('.')
        
        if tiene_comas:
            # Formato colombiano: "6.800.000,50" -> remover puntos (miles) y convertir coma a punto (decimal)
            value = value.replace('.', '')  # Remover puntos de miles
            value = value.replace(',', '.')  # Convertir coma decimal a punto
        elif puntos > 1:
            # Formato colombiano sin decimales: "6.800.000" -> remover todos los puntos
            value = value.replace('.', '')
        elif puntos == 1:
            # Podría ser formato inglés con decimales: "6800000.00"
            # Verificar si el punto está al final o en medio
            partes = value.split('.')
            if len(partes) == 2:
                # Si la parte después del punto tiene más de 3 dígitos, probablemente es formato inglés
                # Si tiene 2 dígitos, podría ser decimales
                if len(partes[1]) <= 2:
                    # Probablemente son decimales, mantener el punto
                    pass  # No remover el punto, se convertirá a float directamente
                else:
                    # Probablemente es formato de miles mal formateado, remover
                    value = value.replace('.', '')
            else:
                value = value.replace('.', '')
        else:
            # No tiene puntos ni comas, está limpio
            pass
        
        # Intentar convertir a float
        try:
            value = float(value)
        except ValueError:
            raise ValueError(f'Ingrese un número válido para {campo_nombre}')
    
    # Validar que sea un número positivo
    if value < 0:
        raise ValueError(f'El valor de {campo_nombre} debe ser positivo')
        
    return value


def limpiar_datos_post_numericos(data, campos_numericos):
    """
    Limpia múltiples campos numéricos de un diccionario de datos POST.
    
    Args:
        data: Diccionario con los datos POST (se modifica in-place)
        campos_numericos: Lista de nombres de campos a limpiar
    
    Returns:
        Diccionario modificado con valores numéricos limpios
    """
    for campo in campos_numericos:
        if campo in data and data[campo]:
            valor = data[campo]
            if isinstance(valor, str):
                # Remover espacios
                valor = valor.strip()
                
                # Remover símbolos de porcentaje
                if valor.endswith('%'):
                    valor = valor[:-1]
                
                # Remover símbolo $
                valor = valor.replace('$', '')
                
                # Detectar formato: colombiano (punto para miles, coma para decimales) o inglés (punto para decimales)
                tiene_comas = ',' in valor
                puntos = valor.count('.')
                
                if tiene_comas:
                    # Formato colombiano: "6.800.000,50" -> remover puntos (miles) y convertir coma a punto (decimal)
                    valor = valor.replace('.', '')  # Remover puntos de miles
                    valor = valor.replace(',', '.')  # Convertir coma decimal a punto
                elif puntos > 1:
                    # Formato colombiano sin decimales: "6.800.000" -> remover todos los puntos
                    valor = valor.replace('.', '')
                elif puntos == 1:
                    # Podría ser formato inglés con decimales: "6800000.00"
                    # Verificar si el punto está al final o en medio
                    partes = valor.split('.')
                    if len(partes) == 2:
                        # Si la parte después del punto tiene más de 3 dígitos, probablemente es formato inglés
                        # Si tiene 2 dígitos, podría ser decimales
                        if len(partes[1]) <= 2:
                            # Probablemente son decimales, mantener el punto
                            pass  # No remover el punto, se convertirá a float directamente
                        else:
                            # Probablemente es formato de miles mal formateado, remover
                            valor = valor.replace('.', '')
                    else:
                        valor = valor.replace('.', '')
                else:
                    # No tiene puntos ni comas, está limpio
                    pass
                
                data[campo] = valor
    
    return data

