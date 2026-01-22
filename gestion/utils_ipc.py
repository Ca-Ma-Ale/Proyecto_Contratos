"""
Funciones utilitarias para el cálculo de ajustes por IPC
"""
from decimal import Decimal
from datetime import date
from django.db.models import Q

from gestion.models import Contrato, IPCHistorico, CalculoIPC, OtroSi
from gestion.utils_otrosi import (
    get_ultimo_otrosi_que_modifico_campo_hasta_fecha,
    get_otrosi_vigente,
)


def _mes_a_numero(mes_str):
    """Convierte el nombre del mes a número"""
    meses = {
        'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4,
        'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
        'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
    }
    return meses.get(mes_str, 1)


def _numero_a_mes(numero):
    """Convierte el número del mes a nombre"""
    meses = {
        1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL',
        5: 'MAYO', 6: 'JUNIO', 7: 'JULIO', 8: 'AGOSTO',
        9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'
    }
    return meses.get(numero, 'ENERO')


def obtener_canon_base_para_ipc(contrato, fecha_aplicacion):
    """
    Obtiene el canon base para calcular el IPC.
    
    Prioridad:
    1. Último cálculo de IPC realizado antes de la fecha de aplicación (cualquier estado)
    2. Canon del Otro Sí vigente que haya modificado el canon fijo hasta el día anterior
    3. Canon mínimo garantizado del Otro Sí vigente (para contratos híbridos)
    4. Canon del contrato base (valor_canon_fijo o canon_minimo_garantizado)
    
    Args:
        contrato: Instancia del modelo Contrato
        fecha_aplicacion: date con la fecha exacta en que se aplica el ajuste por IPC
    
    Returns:
        dict con:
            - canon: Decimal con el valor del canon
            - fuente: str indicando la fuente del canon
            - es_manual: bool indicando si fue ingresado manualmente
    """
    from datetime import timedelta
    
    # Calcular fecha de referencia (día anterior exacto)
    fecha_referencia = fecha_aplicacion - timedelta(days=1)
    
    # 1. Buscar último cálculo de IPC realizado antes de la fecha de referencia
    ultimo_calculo = CalculoIPC.objects.filter(
        contrato=contrato,
        fecha_aplicacion__lt=fecha_aplicacion
    ).order_by('-fecha_aplicacion', '-fecha_calculo').first()
    
    if ultimo_calculo and ultimo_calculo.nuevo_canon:
        return {
            'canon': ultimo_calculo.nuevo_canon,
            'fuente': f'Cálculo IPC {ultimo_calculo.fecha_aplicacion.strftime("%d/%m/%Y")}',
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
            'fuente': 'Contrato Base (Canon Fijo)',
            'es_manual': False,
            'contrato_referencia': contrato
        }
    
    if contrato.canon_minimo_garantizado:
        return {
            'canon': contrato.canon_minimo_garantizado,
            'fuente': 'Contrato Base (Canon Mínimo Garantizado)',
            'es_manual': False,
            'contrato_referencia': contrato
        }
    
    # Si no hay canon disponible, retornar None
    return {
        'canon': None,
        'fuente': 'No disponible',
        'es_manual': False
    }


def obtener_fuente_puntos_adicionales(contrato, fecha_aplicacion):
    """
    Obtiene la fuente de los puntos adicionales IPC para un cálculo.
    
    Prioridad:
    1. Otro Sí vigente que haya modificado los puntos adicionales hasta el día anterior
    2. Contrato base
    
    Args:
        contrato: Instancia del modelo Contrato
        fecha_aplicacion: date con la fecha exacta en que se aplica el ajuste por IPC
    
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


def calcular_ajuste_ipc(canon_anterior, valor_ipc, puntos_adicionales):
    """
    Calcula el ajuste de canon por IPC.
    
    Fórmula: Canon Anterior * (1 + (IPC + Puntos Adicionales) / 100)
    
    Args:
        canon_anterior: Decimal con el canon base
        valor_ipc: Decimal con el valor del IPC en porcentaje
        puntos_adicionales: Decimal con los puntos adicionales en porcentaje
    
    Returns:
        dict con:
            - porcentaje_total: Decimal con el porcentaje total a aplicar
            - valor_incremento: Decimal con el valor del incremento en pesos
            - nuevo_canon: Decimal con el nuevo canon calculado
    """
    if canon_anterior is None or canon_anterior <= 0:
        raise ValueError("El canon anterior debe ser mayor a cero")
    
    # Convertir a Decimal para precisión
    canon_anterior = Decimal(str(canon_anterior))
    valor_ipc = Decimal(str(valor_ipc))
    puntos_adicionales = Decimal(str(puntos_adicionales))
    
    # Calcular porcentaje total
    porcentaje_total = valor_ipc + puntos_adicionales
    
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


def obtener_contratos_pendientes_ajuste_ipc(fecha_referencia=None):
    """
    Obtiene los contratos que requieren ajuste por IPC según su periodicidad.
    
    Args:
        fecha_referencia: date opcional, por defecto usa date.today()
    
    Returns:
        QuerySet de contratos que requieren ajuste
    """
    if fecha_referencia is None:
        fecha_referencia = date.today()
    
    # Contratos con IPC configurado
    contratos = Contrato.objects.filter(
        tipo_condicion_ipc='IPC',
        vigente=True
    ).exclude(
        puntos_adicionales_ipc__isnull=True
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
        calculo_existente = CalculoIPC.objects.filter(
            contrato=contrato,
            fecha_aplicacion=fecha_aumento_anual
        ).exists()
        
        if calculo_existente:
            continue
        
        # Verificar si la fecha de aumento coincide con la fecha de referencia
        if fecha_aumento_anual == fecha_referencia:
            contratos_pendientes.append(contrato)
    
    return contratos_pendientes


def validar_ipc_disponible(año_aplicacion):
    """
    Valida si existe un valor de IPC para el año de aplicación.
    
    La lógica correcta es: en el año X se aplica el IPC del año X-1
    (porque el DANE certifica el IPC del año anterior en el año actual)
    
    Args:
        año_aplicacion: int con el año de aplicación (ej: 2025)
    
    Returns:
        IPCHistorico del año anterior (ej: IPC 2024 para año de aplicación 2025) o None
    """
    año_ipc = año_aplicacion - 1
    try:
        return IPCHistorico.objects.get(año=año_ipc)
    except IPCHistorico.DoesNotExist:
        return None


def obtener_ultimo_calculo_ipc_contrato(contrato):
    """
    Obtiene el último cálculo de IPC realizado para un contrato.
    
    Args:
        contrato: Instancia del modelo Contrato
    
    Returns:
        CalculoIPC o None
    """
    return CalculoIPC.objects.filter(
        contrato=contrato,
        estado__in=['PENDIENTE', 'APLICADO']
    ).order_by('-fecha_aplicacion', '-fecha_calculo').first()


def obtener_ultimo_calculo_ipc_aplicado(contrato):
    """
    Obtiene el último cálculo de IPC aplicado para un contrato.
    Solo incluye cálculos con estado APLICADO.
    
    Args:
        contrato: Instancia del modelo Contrato
    
    Returns:
        CalculoIPC o None si no existe ningún cálculo aplicado
    """
    return CalculoIPC.objects.filter(
        contrato=contrato,
        estado='APLICADO'
    ).order_by('-fecha_aplicacion', '-fecha_calculo').first()


def calcular_proxima_fecha_aumento(contrato, fecha_referencia=None):
    """
    Calcula la próxima fecha de aumento IPC/Salario Mínimo para un contrato.
    
    Si hay un último cálculo realizado, calcula desde la fecha de aplicación del último cálculo + 1 año.
    Si no hay cálculos, calcula desde fecha_inicial_contrato + 1 año o fecha_aumento_ipc + 1 año.
    
    Args:
        contrato: Instancia del modelo Contrato
        fecha_referencia: date opcional, por defecto usa date.today()
    
    Returns:
        date con la próxima fecha de aumento o None si no se puede calcular
    """
    from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo_hasta_fecha
    from gestion.models import CalculoSalarioMinimo
    
    if fecha_referencia is None:
        fecha_referencia = date.today()
    
    # Obtener periodicidad considerando otrosí
    otrosi_periodicidad = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato, 'nueva_periodicidad_ipc', fecha_referencia
    )
    if otrosi_periodicidad and otrosi_periodicidad.nueva_periodicidad_ipc:
        periodicidad = otrosi_periodicidad.nueva_periodicidad_ipc
    else:
        periodicidad = contrato.periodicidad_ipc
    
    # Si es ANUAL
    if periodicidad == 'ANUAL':
        # Obtener último cálculo realizado (IPC o Salario Mínimo)
        ultimo_ipc = CalculoIPC.objects.filter(
            contrato=contrato
        ).order_by('-fecha_aplicacion', '-fecha_calculo').first()
        
        ultimo_salario = CalculoSalarioMinimo.objects.filter(
            contrato=contrato
        ).order_by('-fecha_aplicacion', '-fecha_calculo').first()
        
        # Determinar cuál es el último cálculo más reciente
        ultimo_calculo = None
        if ultimo_ipc and ultimo_salario:
            ultimo_calculo = ultimo_ipc if ultimo_ipc.fecha_aplicacion >= ultimo_salario.fecha_aplicacion else ultimo_salario
        elif ultimo_ipc:
            ultimo_calculo = ultimo_ipc
        elif ultimo_salario:
            ultimo_calculo = ultimo_salario
        
        # Si hay último cálculo, calcular desde su fecha de aplicación + 1 año
        if ultimo_calculo:
            fecha_ultimo_ajuste = ultimo_calculo.fecha_aplicacion
            fecha_proxima = date(
                fecha_ultimo_ajuste.year + 1,
                fecha_ultimo_ajuste.month,
                fecha_ultimo_ajuste.day
            )
            return fecha_proxima
        
        # Si no hay cálculos, calcular desde fecha base o fecha inicial
        # Obtener fecha de aumento considerando otrosí
        otrosi_fecha_ipc = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_fecha_aumento_ipc', fecha_referencia
        )
        if otrosi_fecha_ipc and otrosi_fecha_ipc.nueva_fecha_aumento_ipc:
            fecha_base = otrosi_fecha_ipc.nueva_fecha_aumento_ipc
        else:
            fecha_base = contrato.fecha_aumento_ipc
        
        if fecha_base:
            # Calcular fecha_base + 1 año
            fecha_proxima = date(
                fecha_base.year + 1,
                fecha_base.month,
                fecha_base.day
            )
            return fecha_proxima
        elif contrato.fecha_inicial_contrato:
            # Calcular fecha_inicial + 1 año
            fecha_inicial = contrato.fecha_inicial_contrato
            fecha_proxima = date(
                fecha_inicial.year + 1,
                fecha_inicial.month,
                fecha_inicial.day
            )
            return fecha_proxima
    
    # Si es FECHA_ESPECIFICA
    elif periodicidad == 'FECHA_ESPECIFICA':
        # Obtener fecha de aumento considerando otrosí
        otrosi_fecha_ipc = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_fecha_aumento_ipc', fecha_referencia
        )
        if otrosi_fecha_ipc and otrosi_fecha_ipc.nueva_fecha_aumento_ipc:
            fecha_base = otrosi_fecha_ipc.nueva_fecha_aumento_ipc
        else:
            fecha_base = contrato.fecha_aumento_ipc
        
        if fecha_base:
            return fecha_base
    
    return None


def obtener_ultimo_calculo_ajuste(contrato):
    """
    Obtiene el último cálculo de ajuste (IPC o Salario Mínimo) para un contrato.
    Los cálculos eliminados se borran físicamente de la base de datos.
    
    Args:
        contrato: Instancia del modelo Contrato
    
    Returns:
        CalculoIPC o CalculoSalarioMinimo o None
    """
    from gestion.models import CalculoSalarioMinimo
    
    # Obtener último cálculo de IPC
    ultimo_ipc = CalculoIPC.objects.filter(
        contrato=contrato
    ).order_by('-fecha_aplicacion', '-fecha_calculo').first()
    
    # Obtener último cálculo de Salario Mínimo
    ultimo_salario = CalculoSalarioMinimo.objects.filter(
        contrato=contrato
    ).order_by('-fecha_aplicacion', '-fecha_calculo').first()
    
    # Retornar el más reciente
    if ultimo_ipc and ultimo_salario:
        if ultimo_ipc.fecha_aplicacion >= ultimo_salario.fecha_aplicacion:
            return ultimo_ipc
        else:
            return ultimo_salario
    elif ultimo_ipc:
        return ultimo_ipc
    elif ultimo_salario:
        return ultimo_salario
    
    return None


def obtener_ultimo_calculo_aplicado_hasta_fecha(contrato, fecha_referencia=None):
    """
    Obtiene el último cálculo de ajuste (IPC o Salario Mínimo) aplicado hasta una fecha específica.
    Solo incluye cálculos con estado APLICADO y fecha_aplicacion <= fecha_referencia.
    
    Args:
        contrato: Instancia del modelo Contrato
        fecha_referencia: date opcional, por defecto usa date.today()
    
    Returns:
        CalculoIPC o CalculoSalarioMinimo o None
    """
    from gestion.models import CalculoSalarioMinimo
    
    if fecha_referencia is None:
        fecha_referencia = date.today()
    
    # Obtener último cálculo de IPC aplicado hasta la fecha
    ultimo_ipc = CalculoIPC.objects.filter(
        contrato=contrato,
        estado='APLICADO',
        fecha_aplicacion__lte=fecha_referencia
    ).order_by('-fecha_aplicacion', '-fecha_calculo').first()
    
    # Obtener último cálculo de Salario Mínimo aplicado hasta la fecha
    ultimo_salario = CalculoSalarioMinimo.objects.filter(
        contrato=contrato,
        estado='APLICADO',
        fecha_aplicacion__lte=fecha_referencia
    ).order_by('-fecha_aplicacion', '-fecha_calculo').first()
    
    # Retornar el más reciente
    if ultimo_ipc and ultimo_salario:
        if ultimo_ipc.fecha_aplicacion >= ultimo_salario.fecha_aplicacion:
            return ultimo_ipc
        else:
            return ultimo_salario
    elif ultimo_ipc:
        return ultimo_ipc
    elif ultimo_salario:
        return ultimo_salario
    
    return None


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
    from gestion.models import CalculoSalarioMinimo
    
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


def actualizar_calculos_por_otrosi(contrato, otrosi, usuario_aprobador):
    """
    Actualiza los cálculos de IPC o Salario Mínimo aplicados cuando se aprueba un Otro Sí
    que modifica el canon para el mismo período.
    
    Args:
        contrato: Instancia del modelo Contrato
        otrosi: Instancia del modelo OtroSi que se está aprobando
        usuario_aprobador: Usuario que aprueba el Otro Sí
    
    Returns:
        dict con:
            - actualizados: int con el número de cálculos actualizados
            - detalles: list con información de cada cálculo actualizado
    """
    from gestion.models import CalculoIPC, CalculoSalarioMinimo
    from decimal import Decimal
    from datetime import date
    
    if not (otrosi.nuevo_valor_canon or otrosi.nuevo_canon_minimo_garantizado):
        return {'actualizados': 0, 'detalles': []}
    
    nuevo_valor_canon = otrosi.nuevo_valor_canon or otrosi.nuevo_canon_minimo_garantizado
    año_otrosi = otrosi.effective_from.year
    fecha_otrosi = otrosi.effective_from
    
    detalles = []
    actualizados = 0
    
    # Buscar cálculos aplicados para el año del Otro Sí
    calculos_ipc = CalculoIPC.objects.filter(
        contrato=contrato,
        año_aplicacion=año_otrosi,
        estado='APLICADO'
    )
    
    calculos_sm = CalculoSalarioMinimo.objects.filter(
        contrato=contrato,
        año_aplicacion=año_otrosi,
        estado='APLICADO'
    )
    
    # Actualizar cálculos de IPC
    for calculo in calculos_ipc:
        if abs(calculo.nuevo_canon - nuevo_valor_canon) > Decimal('0.01'):
            valor_anterior = calculo.nuevo_canon
            diferencia = nuevo_valor_canon - calculo.canon_anterior
            porcentaje_aplicado = ((nuevo_valor_canon / calculo.canon_anterior) - Decimal('1')) * Decimal('100') if calculo.canon_anterior > 0 else Decimal('0')
            
            calculo.nuevo_canon = nuevo_valor_canon
            calculo.valor_incremento = diferencia
            calculo.porcentaje_total_aplicar = porcentaje_aplicado
            
            # Agregar nota en observaciones
            nota = f"\n[Actualizado automáticamente por Otro Sí {otrosi.numero_otrosi} aprobado el {date.today().strftime('%d/%m/%Y')}: Valor ajustado de ${valor_anterior:,.2f} a ${nuevo_valor_canon:,.2f}]"
            calculo.observaciones = (calculo.observaciones + nota) if calculo.observaciones else nota.strip()
            
            calculo.save()
            actualizados += 1
            detalles.append({
                'tipo': 'IPC',
                'fecha': calculo.fecha_aplicacion,
                'valor_anterior': valor_anterior,
                'valor_nuevo': nuevo_valor_canon,
            })
    
    # Actualizar cálculos de Salario Mínimo
    for calculo in calculos_sm:
        if abs(calculo.nuevo_canon - nuevo_valor_canon) > Decimal('0.01'):
            valor_anterior = calculo.nuevo_canon
            diferencia = nuevo_valor_canon - calculo.canon_anterior
            porcentaje_aplicado = ((nuevo_valor_canon / calculo.canon_anterior) - Decimal('1')) * Decimal('100') if calculo.canon_anterior > 0 else Decimal('0')
            
            calculo.nuevo_canon = nuevo_valor_canon
            calculo.valor_incremento = diferencia
            calculo.porcentaje_total_aplicar = porcentaje_aplicado
            
            # Agregar nota en observaciones
            nota = f"\n[Actualizado automáticamente por Otro Sí {otrosi.numero_otrosi} aprobado el {date.today().strftime('%d/%m/%Y')}: Valor ajustado de ${valor_anterior:,.2f} a ${nuevo_valor_canon:,.2f}]"
            calculo.observaciones = (calculo.observaciones + nota) if calculo.observaciones else nota.strip()
            
            calculo.save()
            actualizados += 1
            detalles.append({
                'tipo': 'Salario Mínimo',
                'fecha': calculo.fecha_aplicacion,
                'valor_anterior': valor_anterior,
                'valor_nuevo': nuevo_valor_canon,
            })
    
    return {
        'actualizados': actualizados,
        'detalles': detalles,
    }
