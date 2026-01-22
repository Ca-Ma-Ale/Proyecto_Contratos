"""
Funciones utilitarias para el cálculo de ajustes por Salario Mínimo
"""
from decimal import Decimal
from datetime import date
from django.db.models import Q

from gestion.models import Contrato, SalarioMinimoHistorico, CalculoSalarioMinimo, OtroSi
from gestion.utils_otrosi import (
    get_ultimo_otrosi_que_modifico_campo_hasta_fecha,
    get_otrosi_vigente,
)


def obtener_canon_base_para_salario_minimo(contrato, fecha_aplicacion):
    """
    Obtiene el canon base para calcular el ajuste por Salario Mínimo.
    
    Prioridad:
    1. Último cálculo de Salario Mínimo realizado antes de la fecha de aplicación (cualquier estado)
    2. Canon del Otro Sí vigente que haya modificado el canon fijo hasta el día anterior
    3. Canon mínimo garantizado del Otro Sí vigente (para contratos híbridos)
    4. Canon del contrato base (valor_canon_fijo o canon_minimo_garantizado)
    
    Args:
        contrato: Instancia del modelo Contrato
        fecha_aplicacion: date con la fecha exacta en que se aplica el ajuste por Salario Mínimo
    
    Returns:
        dict con:
            - canon: Decimal con el valor del canon
            - fuente: str indicando la fuente del canon
            - es_manual: bool indicando si fue ingresado manualmente
    """
    from datetime import timedelta
    
    # Calcular fecha de referencia (día anterior exacto)
    fecha_referencia = fecha_aplicacion - timedelta(days=1)
    
    # 1. Buscar último cálculo de Salario Mínimo realizado antes de la fecha de referencia
    ultimo_calculo = CalculoSalarioMinimo.objects.filter(
        contrato=contrato,
        fecha_aplicacion__lt=fecha_aplicacion
    ).order_by('-fecha_aplicacion', '-fecha_calculo').first()
    
    if ultimo_calculo and ultimo_calculo.nuevo_canon:
        return {
            'canon': ultimo_calculo.nuevo_canon,
            'fuente': f'Cálculo Salario Mínimo {ultimo_calculo.fecha_aplicacion.strftime("%d/%m/%Y")}',
            'es_manual': False,
            'calculo_referencia': ultimo_calculo
        }
    
    otrosi_canon = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato,
        'nuevo_valor_canon',
        fecha_referencia,
        permitir_futuros=False
    )
    
    if otrosi_canon and otrosi_canon.nuevo_valor_canon:
        return {
            'canon': otrosi_canon.nuevo_valor_canon,
            'fuente': f'Otro Sí {otrosi_canon.numero_otrosi} (Canon Fijo)',
            'es_manual': False,
            'otrosi_referencia': otrosi_canon
        }
    
    # 3. Buscar Otro Sí vigente que haya modificado el canon mínimo garantizado hasta la fecha de referencia
    otrosi_canon_min = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato,
        'nuevo_canon_minimo_garantizado',
        fecha_referencia,
        permitir_futuros=False
    )
    
    if otrosi_canon_min and otrosi_canon_min.nuevo_canon_minimo_garantizado:
        return {
            'canon': otrosi_canon_min.nuevo_canon_minimo_garantizado,
            'fuente': f'Otro Sí {otrosi_canon_min.numero_otrosi} (Canon Mínimo)',
            'es_manual': False,
            'otrosi_referencia': otrosi_canon_min
        }
    
    # 4. Usar canon del contrato base (prioridad: canon fijo > canon mínimo)
    if contrato.valor_canon_fijo:
        return {
            'canon': contrato.valor_canon_fijo,
            'fuente': 'Contrato Base',
            'es_manual': False,
            'contrato_referencia': contrato
        }
    
    if contrato.canon_minimo_garantizado:
        return {
            'canon': contrato.canon_minimo_garantizado,
            'fuente': 'Contrato Base',
            'es_manual': False,
            'contrato_referencia': contrato
        }
    
    # Si no hay canon disponible, retornar None
    return {
        'canon': None,
        'fuente': 'No disponible',
        'es_manual': False
    }


def obtener_fuente_porcentaje_salario_minimo(contrato, fecha_aplicacion):
    """
    Obtiene la fuente del porcentaje de salario mínimo para un cálculo.
    
    Prioridad:
    1. Otro Sí vigente que haya modificado el porcentaje hasta el día anterior
    2. Contrato base
    
    Args:
        contrato: Instancia del modelo Contrato
        fecha_aplicacion: date con la fecha exacta en que se aplica el ajuste por Salario Mínimo
    
    Returns:
        dict con:
            - porcentaje: Decimal con el valor del porcentaje
            - fuente: str indicando la fuente del porcentaje
    """
    from decimal import Decimal
    from datetime import timedelta
    
    # Calcular fecha de referencia (día anterior exacto)
    fecha_referencia = fecha_aplicacion - timedelta(days=1)
    
    # 1. Buscar Otro Sí vigente que haya modificado el porcentaje hasta la fecha de referencia
    # Nota: Necesitaríamos agregar este campo a OtroSi si no existe
    # Por ahora, usamos el porcentaje del contrato base
    porcentaje_contrato = contrato.porcentaje_salario_minimo or Decimal('0')
    return {
        'porcentaje': porcentaje_contrato,
        'fuente': 'Contrato Base',
    }


def obtener_fuente_puntos_adicionales_salario_minimo(contrato, fecha_aplicacion):
    """
    Obtiene la fuente de los puntos adicionales para un cálculo de Salario Mínimo.
    
    Prioridad:
    1. Otro Sí vigente que haya modificado los puntos adicionales hasta el día anterior
    2. Contrato base
    
    Args:
        contrato: Instancia del modelo Contrato
        fecha_aplicacion: date con la fecha exacta en que se aplica el ajuste por Salario Mínimo
    
    Returns:
        dict con:
            - puntos: Decimal con el valor de los puntos
            - fuente: str indicando la fuente de los puntos
    """
    from decimal import Decimal
    from datetime import timedelta
    
    # Calcular fecha de referencia (día anterior exacto)
    fecha_referencia = fecha_aplicacion - timedelta(days=1)
    
    # 1. Buscar Otro Sí vigente que haya modificado los puntos adicionales hasta la fecha de referencia
    otrosi_puntos = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato,
        'nuevos_puntos_adicionales_ipc',
        fecha_referencia,
        permitir_futuros=False
    )
    
    if otrosi_puntos and otrosi_puntos.nuevos_puntos_adicionales_ipc is not None:
        return {
            'puntos': otrosi_puntos.nuevos_puntos_adicionales_ipc,
            'fuente': f'Otro Sí {otrosi_puntos.numero_otrosi}',
        }
    
    # 2. Usar puntos del contrato base
    puntos_contrato = contrato.puntos_adicionales_ipc or Decimal('0')
    return {
        'puntos': puntos_contrato,
        'fuente': 'Contrato Base',
    }


def calcular_ajuste_salario_minimo(canon_anterior, variacion_salario_minimo, puntos_adicionales):
    """
    Calcula el ajuste de canon por Salario Mínimo usando la variación porcentual del salario mínimo.
    
    Fórmula: Canon Anterior * (1 + (Variación Salario Mínimo + Puntos Adicionales) / 100)
    
    Args:
        canon_anterior: Decimal con el canon base
        variacion_salario_minimo: Decimal con la variación porcentual del Salario Mínimo (calculada automáticamente)
        puntos_adicionales: Decimal con los puntos adicionales en porcentaje
    
    Returns:
        dict con:
            - porcentaje_total: Decimal con el porcentaje total a aplicar
            - valor_incremento: Decimal con el valor del incremento en pesos
            - nuevo_canon: Decimal con el nuevo canon calculado
    """
    if canon_anterior is None or canon_anterior <= 0:
        raise ValueError("El canon anterior debe ser mayor a cero")
    
    if variacion_salario_minimo is None:
        raise ValueError("La variación del salario mínimo es requerida")
    
    # Convertir a Decimal para precisión
    canon_anterior = Decimal(str(canon_anterior))
    variacion_salario_minimo = Decimal(str(variacion_salario_minimo))
    puntos_adicionales = Decimal(str(puntos_adicionales)) if puntos_adicionales else Decimal('0')
    
    # Calcular porcentaje total (variación del salario mínimo + puntos adicionales)
    porcentaje_total = variacion_salario_minimo + puntos_adicionales
    
    # Calcular nuevo canon
    factor = Decimal('1') + (porcentaje_total / Decimal('100'))
    nuevo_canon = canon_anterior * factor
    
    # Calcular incremento
    valor_incremento = nuevo_canon - canon_anterior
    
    return {
        'porcentaje_total': porcentaje_total,
        'valor_incremento': valor_incremento,
        'nuevo_canon': nuevo_canon
    }


def obtener_contratos_pendientes_ajuste_salario_minimo(fecha_referencia=None):
    """
    Obtiene los contratos que requieren ajuste por Salario Mínimo según su periodicidad.
    
    Args:
        fecha_referencia: date opcional, por defecto usa date.today()
    
    Returns:
        QuerySet de contratos que requieren ajuste
    """
    if fecha_referencia is None:
        fecha_referencia = date.today()
    
    # Contratos con Salario Mínimo configurado
    contratos = Contrato.objects.filter(
        tipo_condicion_ipc='SALARIO_MINIMO',
        vigente=True
    ).exclude(
        porcentaje_salario_minimo__isnull=True
    )
    
    contratos_pendientes = []
    
    for contrato in contratos:
        if not contrato.fecha_aumento_ipc:
            continue
        
        # Calcular la fecha de aumento para el año actual
        fecha_aumento_anual = date(
            fecha_referencia.year,
            contrato.fecha_aumento_ipc.month,
            contrato.fecha_aumento_ipc.day
        )
        
        # Si la fecha de aumento ya pasó este año, calcular para el próximo año
        if fecha_aumento_anual < fecha_referencia:
            fecha_aumento_anual = date(
                fecha_referencia.year + 1,
                contrato.fecha_aumento_ipc.month,
                contrato.fecha_aumento_ipc.day
            )
        
        # Verificar si ya tiene cálculo para esta fecha exacta
        calculo_existente = CalculoSalarioMinimo.objects.filter(
            contrato=contrato,
            fecha_aplicacion=fecha_aumento_anual
        ).exists()
        
        if calculo_existente:
            continue
        
        # Verificar si la fecha de aumento coincide con la fecha de referencia
        if fecha_aumento_anual == fecha_referencia:
            contratos_pendientes.append(contrato)
    
    return contratos_pendientes


def validar_salario_minimo_disponible(año_aplicacion):
    """
    Valida si existe un valor de Salario Mínimo para el año de aplicación.
    
    La lógica correcta es: en el año X se aplica el Salario Mínimo del año X
    (porque el Salario Mínimo se decreta para el año actual)
    
    Args:
        año_aplicacion: int con el año de aplicación (ej: 2025)
    
    Returns:
        SalarioMinimoHistorico del año de aplicación o None
    """
    try:
        return SalarioMinimoHistorico.objects.get(año=año_aplicacion)
    except SalarioMinimoHistorico.DoesNotExist:
        return None


def obtener_ultimo_calculo_salario_minimo_contrato(contrato):
    """
    Obtiene el último cálculo de Salario Mínimo realizado para un contrato.
    
    Args:
        contrato: Instancia del modelo Contrato
    
    Returns:
        CalculoSalarioMinimo o None
    """
    return CalculoSalarioMinimo.objects.filter(
        contrato=contrato,
        estado__in=['PENDIENTE', 'APLICADO']
    ).order_by('-fecha_aplicacion', '-fecha_calculo').first()


def obtener_ultimo_calculo_salario_minimo_aplicado(contrato):
    """
    Obtiene el último cálculo de Salario Mínimo aplicado para un contrato.
    Solo incluye cálculos con estado APLICADO.
    
    Args:
        contrato: Instancia del modelo Contrato
    
    Returns:
        CalculoSalarioMinimo o None si no existe ningún cálculo aplicado
    """
    return CalculoSalarioMinimo.objects.filter(
        contrato=contrato,
        estado='APLICADO'
    ).order_by('-fecha_aplicacion', '-fecha_calculo').first()


def verificar_otrosi_vigente_para_fecha(contrato, fecha_aplicacion):
    """
    Verifica si existe un Otro Sí vigente que modifica el canon para el año de aplicación.
    
    Si la fecha de aplicación es 01/01/2026, el canon estará activo durante todo el año 2026.
    Por lo tanto, se verifica si hay algún Otro Sí vigente durante el año 2026 que modifique el canon.
    
    Args:
        contrato: Instancia del modelo Contrato
        fecha_aplicacion: date con la fecha de aplicación del cálculo (ej: 01/01/2026)
    
    Returns:
        dict con:
            - existe: bool indicando si existe un otro sí vigente
            - otrosi: OtroSi vigente que modifica el canon o None
            - valor_canon: Decimal con el valor del canon del otro sí o None
    """
    from datetime import date
    from django.db.models import Q
    from gestion.models import OtroSi
    
    # Obtener el año de aplicación
    año_aplicacion = fecha_aplicacion.year
    
    # Definir el rango del año: desde el primer día hasta el último día del año
    primer_dia_año = date(año_aplicacion, 1, 1)
    ultimo_dia_año = date(año_aplicacion, 12, 31)
    
    # Buscar Otros Sí aprobados que modifiquen el canon y que estén vigentes durante el año
    # Un Otro Sí está vigente en un año si:
    # - effective_from <= ultimo_dia_año (empieza antes o durante el año)
    # - (effective_to >= primer_dia_año O effective_to es None) (termina después o durante el año, o no tiene fin)
    otrosi_canon = OtroSi.objects.filter(
        contrato=contrato,
        estado='APROBADO',
        nuevo_valor_canon__isnull=False,
        effective_from__lte=ultimo_dia_año
    ).filter(
        Q(effective_to__gte=primer_dia_año) | Q(effective_to__isnull=True)
    ).order_by('-effective_from', '-version').first()
    
    if otrosi_canon and otrosi_canon.nuevo_valor_canon:
        return {
            'existe': True,
            'otrosi': otrosi_canon,
            'valor_canon': otrosi_canon.nuevo_valor_canon,
        }
    
    # También verificar canon mínimo garantizado
    otrosi_canon_min = OtroSi.objects.filter(
        contrato=contrato,
        estado='APROBADO',
        nuevo_canon_minimo_garantizado__isnull=False,
        effective_from__lte=ultimo_dia_año
    ).filter(
        Q(effective_to__gte=primer_dia_año) | Q(effective_to__isnull=True)
    ).order_by('-effective_from', '-version').first()
    
    if otrosi_canon_min and otrosi_canon_min.nuevo_canon_minimo_garantizado:
        return {
            'existe': True,
            'otrosi': otrosi_canon_min,
            'valor_canon': otrosi_canon_min.nuevo_canon_minimo_garantizado,
        }
    
    return {
        'existe': False,
        'otrosi': None,
        'valor_canon': None,
    }


def verificar_calculo_existente_para_fecha(contrato, fecha_aplicacion):
    """
    Verifica si existe un cálculo de IPC o Salario Mínimo para una fecha específica.
    
    Args:
        contrato: Instancia del modelo Contrato
        fecha_aplicacion: date con la fecha de aplicación
    
    Returns:
        dict con:
            - existe: bool indicando si existe un cálculo
            - calculo: CalculoIPC o CalculoSalarioMinimo o None
            - tipo: str con 'IPC' o 'SALARIO_MINIMO' o None
    """
    from gestion.models import CalculoIPC
    
    # Buscar cálculo de IPC para esta fecha exacta
    calculo_ipc = CalculoIPC.objects.filter(
        contrato=contrato,
        fecha_aplicacion=fecha_aplicacion
    ).first()
    
    if calculo_ipc:
        return {
            'existe': True,
            'calculo': calculo_ipc,
            'tipo': 'IPC',
        }
    
    # Buscar cálculo de Salario Mínimo para esta fecha exacta
    calculo_salario = CalculoSalarioMinimo.objects.filter(
        contrato=contrato,
        fecha_aplicacion=fecha_aplicacion
    ).first()
    
    if calculo_salario:
        return {
            'existe': True,
            'calculo': calculo_salario,
            'tipo': 'SALARIO_MINIMO',
        }
    
    return {
        'existe': False,
        'calculo': None,
        'tipo': None,
    }

