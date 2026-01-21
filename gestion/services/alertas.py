"""
Servicios relacionados con el cálculo y provisión de alertas.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from django.db import models
from django.db.models import QuerySet
from django.utils import timezone

from gestion.models import Contrato, MESES_CHOICES, Poliza, CalculoIPC, CalculoSalarioMinimo, obtener_nombre_tipo_condicion_ipc
from django.db.models import Q
from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo_hasta_fecha
from gestion.utils_ipc import obtener_contratos_pendientes_ajuste_ipc

_MESES_NUMEROS = {clave: indice + 1 for indice, (clave, _) in enumerate(MESES_CHOICES)}


def obtener_numero_evento(evento):
    """
    Obtiene el número de un evento (OtroSi o RenovacionAutomatica).
    Retorna None si el evento es None.
    """
    if evento is None:
        return None
    # RenovacionAutomatica tiene numero_renovacion
    if hasattr(evento, 'numero_renovacion'):
        return evento.numero_renovacion
    # OtroSi tiene numero_otrosi
    elif hasattr(evento, 'numero_otrosi'):
        return evento.numero_otrosi
    return None


@dataclass(frozen=True)
class AlertaIPC:
    contrato: Contrato
    meses_restantes: int
    color_alerta: str
    mes_ajuste: str
    condicion_ipc: str
    otrosi_modificador: Optional[str] = None
    
    @property
    def meses_restantes_abs(self):
        """Retorna el valor absoluto de meses restantes para mostrar en templates"""
        return abs(self.meses_restantes)


@dataclass(frozen=True)
class AlertaSalarioMinimo:
    contrato: Contrato
    meses_restantes: int
    color_alerta: str
    mes_ajuste: str
    condicion_salario_minimo: str
    otrosi_modificador: Optional[str] = None
    
    @property
    def meses_restantes_abs(self):
        """Retorna el valor absoluto de meses restantes para mostrar en templates"""
        return abs(self.meses_restantes)


def _obtener_fecha_final_contrato(contrato: Contrato, fecha_referencia: date) -> Optional[date]:
    """
    Obtiene la fecha final actualizada de un contrato considerando Otrosí vigentes.
    
    Args:
        contrato: Contrato del cual obtener la fecha final.
        fecha_referencia: Fecha de referencia para evaluar Otrosí vigentes.
    
    Returns:
        Fecha final actualizada o None si no existe.
    """
    otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato, 'nueva_fecha_final_actualizada', fecha_referencia
    )
    if otrosi_modificador and otrosi_modificador.nueva_fecha_final_actualizada:
        return otrosi_modificador.nueva_fecha_final_actualizada
    return contrato.fecha_final_actualizada or contrato.fecha_final_inicial


def obtener_alertas_expiracion_contratos(
    fecha_referencia: Optional[date] = None,
    ventana_dias: int = 90,
    tipo_contrato_cp: Optional[str] = None,
) -> List[Contrato]:
    """
    Obtiene contratos que vencen dentro de la ventana indicada.
    Considera la fecha final actualizada del último Otrosí aprobado.

    Args:
        fecha_referencia: Fecha base para calcular la ventana.
        ventana_dias: Ventana en días hacia adelante para evaluar vencimientos.
        tipo_contrato_cp: Filtro opcional por tipo de contrato (CLIENTE/PROVEEDOR).
    """
    fecha_base = fecha_referencia or timezone.now().date()
    fecha_limite = fecha_base + timedelta(days=ventana_dias)
    
    contratos_vigentes = (
        Contrato.objects.filter(vigente=True)
        .select_related('arrendatario', 'proveedor', 'local')
        .prefetch_related('otrosi')
    )
    
    if tipo_contrato_cp:
        contratos_vigentes = contratos_vigentes.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cp)
    
    alertas_con_fecha = []
    for contrato in contratos_vigentes:
        # Obtener la fecha final actualizada usando efecto cadena (considera otrosí vigentes hasta fecha_referencia)
        fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_base)
        
        if fecha_final_actual and fecha_base <= fecha_final_actual <= fecha_limite:
            alertas_con_fecha.append((contrato, fecha_final_actual))
    
    # Ordenar por fecha final actualizada
    alertas_con_fecha.sort(key=lambda x: x[1])
    
    return [contrato for contrato, _ in alertas_con_fecha]


def obtener_alertas_ipc(
    fecha_referencia: Optional[date] = None,
    tipo_contrato_cp: Optional[str] = None,
) -> List[AlertaIPC]:
    """
    Calcula las alertas de IPC para contratos con configuración de ajuste.
    Considera los valores actualizados del último Otrosí aprobado.

    Args:
        fecha_referencia: Fecha base opcional para evaluar los meses restantes.
        tipo_contrato_cp: Filtro opcional por tipo de contrato (CLIENTE/PROVEEDOR).

    Returns:
        Lista ordenada de alertas de IPC.
    """
    fecha_base = fecha_referencia or timezone.now().date()
    contratos_con_ipc = (
        Contrato.objects.filter(
            vigente=True,
        )
        .select_related('arrendatario', 'proveedor', 'local')
        .prefetch_related('otrosi')
        .order_by('num_contrato')
    )
    
    if tipo_contrato_cp:
        contratos_con_ipc = contratos_con_ipc.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cp)

    alertas: List[AlertaIPC] = []
    for contrato in contratos_con_ipc:
        # Obtener valores actualizados de IPC usando efecto cadena (considera otrosí vigentes hasta fecha_referencia)
        otrosi_tipo_ipc = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nuevo_tipo_condicion_ipc', fecha_base
        )
        otrosi_periodicidad = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_periodicidad_ipc', fecha_base
        )
        otrosi_fecha_ipc = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_fecha_aumento_ipc', fecha_base
        )
        
        tipo_condicion_ipc = (
            otrosi_tipo_ipc.nuevo_tipo_condicion_ipc
            if otrosi_tipo_ipc and otrosi_tipo_ipc.nuevo_tipo_condicion_ipc
            else contrato.tipo_condicion_ipc
        )
        
        periodicidad_ipc = (
            otrosi_periodicidad.nueva_periodicidad_ipc
            if otrosi_periodicidad and otrosi_periodicidad.nueva_periodicidad_ipc
            else contrato.periodicidad_ipc
        )
        
        fecha_aumento_ipc = (
            otrosi_fecha_ipc.nueva_fecha_aumento_ipc
            if otrosi_fecha_ipc and otrosi_fecha_ipc.nueva_fecha_aumento_ipc
            else contrato.fecha_aumento_ipc
        )
        
        # Solo procesar si tiene tipo de condición IPC configurado
        if not tipo_condicion_ipc or tipo_condicion_ipc != 'IPC':
            continue
            
        # Procesar si tiene periodicidad ANUAL
        if periodicidad_ipc not in ['ANUAL']:
            continue
        
        # La fecha de aumento es obligatoria
        if not fecha_aumento_ipc:
            continue
        
        # Calcular la fecha de aumento para el año actual
        fecha_aumento_anual = date(
            fecha_base.year,
            fecha_aumento_ipc.month,
            fecha_aumento_ipc.day
        )
        
        # Si la fecha de aumento ya pasó este año, calcular para el próximo año
        if fecha_aumento_anual < fecha_base:
            fecha_aumento_anual = date(
                fecha_base.year + 1,
                fecha_aumento_ipc.month,
                fecha_aumento_ipc.day
            )
        
        # Verificar si ya tiene cálculo para esta fecha exacta
        calculo_existente = CalculoIPC.objects.filter(
            contrato=contrato,
            fecha_aplicacion=fecha_aumento_anual,
            estado__in=['PENDIENTE', 'APLICADO']
        ).exists()
        
        # Si ya tiene cálculo aplicado, no mostrar la alerta
        if calculo_existente:
            continue
        
        # Calcular días restantes hasta el próximo ajuste
        dias_restantes = (fecha_aumento_anual - fecha_base).days
        
        # Convertir días a meses usando estándar de 30 días por mes
        meses_restantes = round(dias_restantes / 30)
        
        # Mostrar alertas si:
        # 1. La fecha ya pasó (dias_restantes < 0) - siempre mostrar
        # 2. La fecha está dentro de 3 meses (90 días) en el futuro
        if dias_restantes > 90:
            continue
        
        # Determinar color de alerta
        # Si la fecha ya pasó (dias_restantes negativo), mostrar como crítica
        if dias_restantes < 0:
            color_alerta = 'danger'
        elif dias_restantes <= 7:
            color_alerta = 'danger'
        elif dias_restantes <= 30:
            color_alerta = 'warning'
        else:
            color_alerta = 'success'

        # Obtener display de la fecha y condición IPC
        fecha_ajuste_display = fecha_aumento_anual.strftime('%d/%m/%Y')
        condicion_ipc_display = obtener_nombre_tipo_condicion_ipc(tipo_condicion_ipc) if tipo_condicion_ipc else None

        # Determinar qué Otrosí modificó estos valores (prioridad: fecha > periodicidad > tipo)
        otrosi_modificador_numero = None
        if otrosi_fecha_ipc:
            otrosi_modificador_numero = obtener_numero_evento(otrosi_fecha_ipc)
        elif otrosi_periodicidad:
            otrosi_modificador_numero = obtener_numero_evento(otrosi_periodicidad)
        elif otrosi_tipo_ipc:
            otrosi_modificador_numero = obtener_numero_evento(otrosi_tipo_ipc)

        alertas.append(
            AlertaIPC(
                contrato=contrato,
                meses_restantes=meses_restantes,
                color_alerta=color_alerta,
                mes_ajuste=fecha_ajuste_display,
                condicion_ipc=condicion_ipc_display,
                otrosi_modificador=otrosi_modificador_numero,
            )
        )

    return sorted(
        alertas,
        key=lambda alerta: (
            0
            if alerta.color_alerta == 'danger'
            else 1
            if alerta.color_alerta == 'warning'
            else 2,
            alerta.meses_restantes,
            alerta.contrato.num_contrato,
        ),
    )


def obtener_alertas_salario_minimo(
    fecha_referencia: Optional[date] = None,
    tipo_contrato_cp: Optional[str] = None,
) -> List[AlertaSalarioMinimo]:
    """
    Calcula las alertas de Salario Mínimo para contratos con configuración de ajuste.
    Considera los valores actualizados del último Otrosí aprobado.

    Args:
        fecha_referencia: Fecha base opcional para evaluar los meses restantes.
        tipo_contrato_cp: Filtro opcional por tipo de contrato (CLIENTE/PROVEEDOR).

    Returns:
        Lista ordenada de alertas de Salario Mínimo.
    """
    fecha_base = fecha_referencia or timezone.now().date()
    contratos_con_sm = (
        Contrato.objects.filter(
            vigente=True,
        )
        .select_related('arrendatario', 'proveedor', 'local')
        .prefetch_related('otrosi')
        .order_by('num_contrato')
    )
    
    if tipo_contrato_cp:
        contratos_con_sm = contratos_con_sm.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cp)

    alertas: List[AlertaSalarioMinimo] = []
    for contrato in contratos_con_sm:
        # Obtener valores actualizados usando efecto cadena (considera otrosí vigentes hasta fecha_referencia)
        otrosi_tipo_ipc = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nuevo_tipo_condicion_ipc', fecha_base
        )
        otrosi_periodicidad = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_periodicidad_ipc', fecha_base
        )
        otrosi_fecha_ipc = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_fecha_aumento_ipc', fecha_base
        )
        
        tipo_condicion_ipc = (
            otrosi_tipo_ipc.nuevo_tipo_condicion_ipc
            if otrosi_tipo_ipc and otrosi_tipo_ipc.nuevo_tipo_condicion_ipc
            else contrato.tipo_condicion_ipc
        )
        
        periodicidad_ipc = (
            otrosi_periodicidad.nueva_periodicidad_ipc
            if otrosi_periodicidad and otrosi_periodicidad.nueva_periodicidad_ipc
            else contrato.periodicidad_ipc
        )
        
        fecha_aumento_ipc = (
            otrosi_fecha_ipc.nueva_fecha_aumento_ipc
            if otrosi_fecha_ipc and otrosi_fecha_ipc.nueva_fecha_aumento_ipc
            else contrato.fecha_aumento_ipc
        )
        
        # Solo procesar si tiene tipo de condición SALARIO_MINIMO configurado
        if not tipo_condicion_ipc or tipo_condicion_ipc != 'SALARIO_MINIMO':
            continue
            
        # Procesar si tiene periodicidad ANUAL
        if periodicidad_ipc not in ['ANUAL']:
            continue
        
        # La fecha de aumento es obligatoria
        if not fecha_aumento_ipc:
            continue
        
        # Calcular la fecha de aumento para el año actual
        fecha_aumento_anual = date(
            fecha_base.year,
            fecha_aumento_ipc.month,
            fecha_aumento_ipc.day
        )
        
        # Si la fecha de aumento ya pasó este año, calcular para el próximo año
        if fecha_aumento_anual < fecha_base:
            fecha_aumento_anual = date(
                fecha_base.year + 1,
                fecha_aumento_ipc.month,
                fecha_aumento_ipc.day
            )
        
        # Verificar si ya tiene cálculo para esta fecha exacta
        calculo_existente = CalculoSalarioMinimo.objects.filter(
            contrato=contrato,
            fecha_aplicacion=fecha_aumento_anual,
            estado__in=['PENDIENTE', 'APLICADO']
        ).exists()
        
        # Si ya tiene cálculo aplicado, no mostrar la alerta
        if calculo_existente:
            continue
        
        # Calcular días restantes hasta el próximo ajuste
        dias_restantes = (fecha_aumento_anual - fecha_base).days
        
        # Convertir días a meses usando estándar de 30 días por mes
        meses_restantes = round(dias_restantes / 30)
        
        # Mostrar alertas si:
        # 1. La fecha ya pasó (dias_restantes < 0) - siempre mostrar
        # 2. La fecha está dentro de 3 meses (90 días) en el futuro
        if dias_restantes > 90:
            continue
        
        # Determinar color de alerta
        # Si la fecha ya pasó (dias_restantes negativo), mostrar como crítica
        if dias_restantes < 0:
            color_alerta = 'danger'
        elif dias_restantes <= 7:
            color_alerta = 'danger'
        elif dias_restantes <= 30:
            color_alerta = 'warning'
        else:
            color_alerta = 'success'

        # Obtener display de la fecha y condición
        fecha_ajuste_display = fecha_aumento_anual.strftime('%d/%m/%Y')
        condicion_sm_display = obtener_nombre_tipo_condicion_ipc(tipo_condicion_ipc) if tipo_condicion_ipc else None

        # Determinar qué Otrosí modificó estos valores (prioridad: fecha > periodicidad > tipo)
        otrosi_modificador_numero = None
        if otrosi_fecha_ipc:
            otrosi_modificador_numero = obtener_numero_evento(otrosi_fecha_ipc)
        elif otrosi_periodicidad:
            otrosi_modificador_numero = obtener_numero_evento(otrosi_periodicidad)
        elif otrosi_tipo_ipc:
            otrosi_modificador_numero = obtener_numero_evento(otrosi_tipo_ipc)

        alertas.append(
            AlertaSalarioMinimo(
                contrato=contrato,
                meses_restantes=meses_restantes,
                color_alerta=color_alerta,
                mes_ajuste=fecha_ajuste_display,
                condicion_salario_minimo=condicion_sm_display,
                otrosi_modificador=otrosi_modificador_numero,
            )
        )

    return sorted(
        alertas,
        key=lambda alerta: (
            0
            if alerta.color_alerta == 'danger'
            else 1
            if alerta.color_alerta == 'warning'
            else 2,
            alerta.meses_restantes,
            alerta.contrato.num_contrato,
        ),
    )


def obtener_polizas_criticas(
    fecha_referencia: Optional[date] = None,
    ventana_dias: int = 60,
    tipo_contrato_cp: Optional[str] = None,
) -> List[Poliza]:
    """
    Obtiene pólizas con problemas de vigencia o pendientes de aporte.
    Incluye pólizas vencidas o que vencen dentro de la ventana de días especificada.
    Solo incluye pólizas de contratos vigentes (verificado por fechas al día de hoy).

    Args:
        fecha_referencia: Fecha base para evaluar vencimientos.
        ventana_dias: Ventana de evaluación para las vigencias próximas.
        tipo_contrato_cp: Filtro opcional por tipo de contrato (CLIENTE/PROVEEDOR).
    
    Returns:
        Lista de pólizas críticas ordenadas por fecha de vencimiento.
    """
    fecha_base = fecha_referencia or timezone.now().date()
    fecha_limite = fecha_base + timedelta(days=ventana_dias)
    
    # Obtener todas las pólizas que cumplen los criterios de fecha
    polizas_candidatas = (
        Poliza.objects.filter(
            fecha_vencimiento__isnull=False,
            fecha_vencimiento__lte=fecha_limite
        )
        .select_related('contrato', 'contrato__arrendatario', 'contrato__proveedor')
        .order_by('fecha_vencimiento')
    )
    
    if tipo_contrato_cp:
        polizas_candidatas = polizas_candidatas.filter(contrato__tipo_contrato_cliente_proveedor=tipo_contrato_cp)
    
    # Filtrar solo las de contratos vigentes (verificado por fechas)
    polizas_criticas = []
    for poliza in polizas_candidatas:
        contrato = poliza.contrato
        
        # Verificar vigencia basándose en fechas, no solo en el campo booleano
        # Considerar Otrosí que puedan haber modificado la fecha final
        fecha_final_contrato = _obtener_fecha_final_contrato(contrato, fecha_base)
        
        # El contrato está vigente si:
        # 1. Tiene fecha final y no ha pasado
        # 2. O no tiene fecha final (contrato indefinido)
        # 3. Y la fecha inicial ya pasó o es hoy
        fecha_inicial = contrato.fecha_inicial_contrato
        
        if fecha_inicial and fecha_inicial > fecha_base:
            # El contrato aún no ha iniciado
            continue
        
        # Verificar que el contrato no haya vencido
        if fecha_final_contrato:
            # El contrato está vigente solo si la fecha final es mayor o igual a la fecha base
            if fecha_final_contrato < fecha_base:
                # El contrato ya venció
                continue
        # Si no tiene fecha final, se considera vigente (contrato indefinido)
        
        polizas_criticas.append(poliza)
    
    return polizas_criticas


def obtener_alertas_preaviso(
    fecha_referencia: Optional[date] = None,
    ventana_dias: int = 60,
    tipo_contrato_cp: Optional[str] = None,
) -> List[Contrato]:
    """
    Obtiene contratos que requieren preaviso de renovación.
    Considera la fecha final actualizada y prórroga automática del último Otrosí aprobado.

    Args:
        fecha_referencia: Fecha base para evaluar el preaviso.
        ventana_dias: Ventana máxima para considerar el aviso.
        tipo_contrato_cp: Filtro opcional por tipo de contrato (CLIENTE/PROVEEDOR).
    """
    fecha_base = fecha_referencia or timezone.now().date()
    fecha_limite = fecha_base + timedelta(days=ventana_dias)
    
    contratos_vigentes = (
        Contrato.objects.filter(vigente=True)
        .select_related('arrendatario', 'proveedor', 'local')
        .prefetch_related('otrosi')
    )
    
    if tipo_contrato_cp:
        contratos_vigentes = contratos_vigentes.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cp)
    
    alertas_con_fecha = []
    for contrato in contratos_vigentes:
        # Obtener la fecha final actualizada usando efecto cadena (considera otrosí vigentes hasta fecha_referencia)
        fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_base)
        
        # Usar prórroga automática del contrato (no existe campo en OtroSi para esto)
        prorroga_automatica = contrato.prorroga_automatica
        
        if fecha_final_actual and fecha_final_actual <= fecha_limite and not prorroga_automatica:
            alertas_con_fecha.append((contrato, fecha_final_actual))
    
    # Ordenar por fecha final actualizada
    alertas_con_fecha.sort(key=lambda x: x[1])
    
    return [contrato for contrato, _ in alertas_con_fecha]


@dataclass(frozen=True)
class AlertaPolizaRequerida:
    contrato: Contrato
    tipo_poliza: str
    nombre_poliza: str
    valor_requerido: Optional[Decimal]
    fecha_fin_requerida: Optional[date]
    tiene_poliza: bool
    poliza_vigente: Optional[Poliza]
    otrosi_modificador: Optional[str] = None


def obtener_alertas_polizas_requeridas_no_aportadas(
    fecha_referencia: Optional[date] = None,
    tipo_contrato_cp: Optional[str] = None,
) -> List[AlertaPolizaRequerida]:
    """
    Obtiene alertas de contratos con pólizas requeridas no aportadas o vencidas.
    Aplica el efecto cadena para considerar modificaciones de Otrosí vigentes.
    
    Args:
        fecha_referencia: Fecha base para evaluar los requisitos y vigencias.
        tipo_contrato_cp: Filtro opcional por tipo de contrato (CLIENTE/PROVEEDOR).
    
    Returns:
        Lista ordenada de alertas de pólizas requeridas no aportadas.
    """
    from gestion.utils_otrosi import get_polizas_requeridas_contrato
    from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo_hasta_fecha
    
    fecha_base = fecha_referencia or timezone.now().date()
    
    contratos_vigentes = (
        Contrato.objects.filter(vigente=True)
        .select_related('arrendatario', 'proveedor', 'local')
        .prefetch_related('otrosi', 'polizas')
    )
    
    if tipo_contrato_cp:
        contratos_vigentes = contratos_vigentes.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cp)
    
    alertas: List[AlertaPolizaRequerida] = []
    
    for contrato in contratos_vigentes:
        # Verificar que el contrato esté vigente por fechas
        fecha_final_contrato = _obtener_fecha_final_contrato(contrato, fecha_base)
        fecha_inicial = contrato.fecha_inicial_contrato
        
        if fecha_inicial and fecha_inicial > fecha_base:
            continue
        
        if fecha_final_contrato and fecha_final_contrato < fecha_base:
            continue
        
        # Obtener pólizas requeridas aplicando efecto cadena
        polizas_requeridas = get_polizas_requeridas_contrato(contrato, fecha_base)
        
        if not polizas_requeridas:
            continue
        
        # Obtener pólizas vigentes del contrato
        polizas_contrato = contrato.polizas.filter(
            fecha_vencimiento__gte=fecha_base
        )
        
        # Verificar cada tipo de póliza requerida
        for tipo_poliza, requisitos in polizas_requeridas.items():
            nombre_poliza = requisitos.get('nombre', tipo_poliza)
            valor_requerido = requisitos.get('valor_requerido')
            fecha_fin_requerida = requisitos.get('fecha_fin_requerida')
            
            # Verificar explícitamente que el contrato realmente exige esta póliza
            # usando efecto cadena para considerar Otrosí vigentes
            campo_exigencia_map = {
                'RCE - Responsabilidad Civil': ('nuevo_exige_poliza_rce', 'exige_poliza_rce'),
                'Cumplimiento': ('nuevo_exige_poliza_cumplimiento', 'exige_poliza_cumplimiento'),
                'Poliza de Arrendamiento': ('nuevo_exige_poliza_arrendamiento', 'exige_poliza_arrendamiento'),
                'Arrendamiento': ('nuevo_exige_poliza_todo_riesgo', 'exige_poliza_todo_riesgo'),
                'Otra': ('nuevo_exige_poliza_otra_1', 'exige_poliza_otra_1'),
            }
            
            campo_exigencia_info = campo_exigencia_map.get(tipo_poliza)
            if campo_exigencia_info:
                campo_otrosi, campo_contrato = campo_exigencia_info
                otrosi_exigencia = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
                    contrato, campo_otrosi, fecha_base
                )
                
                if otrosi_exigencia:
                    exige_poliza = bool(getattr(otrosi_exigencia, campo_otrosi, False))
                else:
                    exige_poliza = bool(getattr(contrato, campo_contrato, False))
                
                # Si el contrato no exige esta póliza, saltar esta alerta
                if not exige_poliza:
                    continue
            
            # Buscar póliza vigente del tipo requerido
            poliza_vigente = polizas_contrato.filter(tipo=tipo_poliza).first()
            
            # Si no hay póliza vigente, o si la póliza vigente vence antes de la fecha requerida
            tiene_poliza_valida = False
            poliza_valida = None
            
            if poliza_vigente:
                # Verificar que la póliza vigente cubra hasta la fecha requerida
                if fecha_fin_requerida:
                    if poliza_vigente.fecha_vencimiento >= fecha_fin_requerida:
                        tiene_poliza_valida = True
                        poliza_valida = poliza_vigente
                else:
                    # Si no hay fecha fin requerida, cualquier póliza vigente es válida
                    tiene_poliza_valida = True
                    poliza_valida = poliza_vigente
            
            if not tiene_poliza_valida:
                # Determinar qué Otrosí modificó estos requisitos
                otrosi_modificador_numero = None
                
                # Buscar el Otrosí que modificó la exigencia de esta póliza
                campo_exigencia_map = {
                    'RCE - Responsabilidad Civil': 'nuevo_exige_poliza_rce',
                    'Cumplimiento': 'nuevo_exige_poliza_cumplimiento',
                    'Poliza de Arrendamiento': 'nuevo_exige_poliza_arrendamiento',
                    'Arrendamiento': 'nuevo_exige_poliza_todo_riesgo',
                    'Otra': 'nuevo_exige_poliza_otra_1',
                }
                
                campo_exigencia = campo_exigencia_map.get(tipo_poliza)
                if campo_exigencia:
                    otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
                        contrato, campo_exigencia, fecha_base
                    )
                    otrosi_modificador_numero = obtener_numero_evento(otrosi_modificador)
                
                alertas.append(
                    AlertaPolizaRequerida(
                        contrato=contrato,
                        tipo_poliza=tipo_poliza,
                        nombre_poliza=nombre_poliza,
                        valor_requerido=valor_requerido,
                        fecha_fin_requerida=fecha_fin_requerida,
                        tiene_poliza=poliza_vigente is not None,
                        poliza_vigente=poliza_valida,
                        otrosi_modificador=otrosi_modificador_numero,
                    )
                )
    
    return sorted(
        alertas,
        key=lambda alerta: (
            alerta.contrato.num_contrato,
            alerta.tipo_poliza,
        ),
    )


@dataclass(frozen=True)
class AlertaTerminacionAnticipada:
    contrato: Contrato
    fecha_final_actualizada: date
    dias_restantes: int
    dias_terminacion_anticipada: int
    fecha_limite_terminacion: date
    otrosi_modificador: Optional[str] = None


@dataclass(frozen=True)
class AlertaRenovacionAutomatica:
    contrato: Contrato
    fecha_final_actualizada: date
    dias_restantes: int
    duracion_inicial_meses: int
    otrosi_modificador: Optional[str] = None


def obtener_alertas_terminacion_anticipada(
    fecha_referencia: Optional[date] = None,
    tipo_contrato_cp: Optional[str] = None,
) -> List[AlertaTerminacionAnticipada]:
    """
    Obtiene alertas de contratos que están dentro del período de terminación anticipada.
    Considera la fecha final actualizada y días de terminación del último Otrosí aprobado.
    
    Un contrato está dentro del período de terminación anticipada cuando:
    - Los días restantes hasta el vencimiento son menores o iguales a los días de terminación anticipada configurados.
    
    Args:
        fecha_referencia: Fecha base para evaluar el período de terminación anticipada.
        tipo_contrato_cp: Filtro opcional por tipo de contrato (CLIENTE/PROVEEDOR).
    
    Returns:
        Lista ordenada de alertas de terminación anticipada.
    """
    fecha_base = fecha_referencia or timezone.now().date()
    
    contratos_vigentes = (
        Contrato.objects.filter(vigente=True)
        .select_related('arrendatario', 'proveedor', 'local')
        .prefetch_related('otrosi')
    )
    
    if tipo_contrato_cp:
        contratos_vigentes = contratos_vigentes.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cp)
    
    alertas: List[AlertaTerminacionAnticipada] = []
    
    for contrato in contratos_vigentes:
        # Obtener la fecha final actualizada usando efecto cadena
        fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_base)
        
        if not fecha_final_actual:
            continue
        
        # Verificar que el contrato esté vigente
        fecha_inicial = contrato.fecha_inicial_contrato
        if fecha_inicial and fecha_inicial > fecha_base:
            continue
        
        if fecha_final_actual < fecha_base:
            continue
        
        # Obtener días de terminación anticipada (no hay campo en OtroSi para esto, usar del contrato)
        dias_terminacion = contrato.dias_terminacion_anticipada or 0
        
        if dias_terminacion <= 0:
            continue
        
        # Calcular días restantes hasta el vencimiento
        dias_restantes = (fecha_final_actual - fecha_base).days
        
        # Si los días restantes son menores o iguales a los días de terminación anticipada,
        # el contrato está dentro del período de terminación anticipada
        if dias_restantes <= dias_terminacion and dias_restantes >= 0:
            # Calcular fecha límite para ejercer terminación anticipada
            fecha_limite_terminacion = fecha_final_actual - timedelta(days=dias_terminacion)
            
            # Determinar qué Otrosí modificó la fecha final
            otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
                contrato, 'nueva_fecha_final_actualizada', fecha_base
            )
            otrosi_modificador_numero = obtener_numero_evento(otrosi_modificador)
            
            alertas.append(
                AlertaTerminacionAnticipada(
                    contrato=contrato,
                    fecha_final_actualizada=fecha_final_actual,
                    dias_restantes=dias_restantes,
                    dias_terminacion_anticipada=dias_terminacion,
                    fecha_limite_terminacion=fecha_limite_terminacion,
                    otrosi_modificador=otrosi_modificador_numero,
                )
            )
    
    return sorted(
        alertas,
        key=lambda alerta: (
            alerta.dias_restantes,
            alerta.contrato.num_contrato,
        ),
    )


def obtener_alertas_renovacion_automatica(
    fecha_referencia: Optional[date] = None,
    ventana_dias: int = 30,
) -> List[AlertaRenovacionAutomatica]:
    """
    Obtiene alertas de contratos con prórroga automática que están vencidos o próximos a vencer.
    Estos contratos requieren autorización del usuario para renovar automáticamente.
    
    Excluye contratos que ya tienen renovaciones automáticas aprobadas, ya que estas
    ya fueron gestionadas y extienden el contrato.
    
    Args:
        fecha_referencia: Fecha base para evaluar vencimientos.
        ventana_dias: Ventana en días hacia adelante para considerar contratos próximos a vencer.
    
    Returns:
        Lista ordenada de alertas de renovación automática.
    """
    from gestion.models import RenovacionAutomatica
    
    fecha_base = fecha_referencia or timezone.now().date()
    fecha_limite = fecha_base + timedelta(days=ventana_dias)
    
    contratos_vigentes = (
        Contrato.objects.filter(
            vigente=True,
            prorroga_automatica=True
        )
        .select_related('arrendatario', 'proveedor', 'local', 'tipo_servicio')
        .prefetch_related('otrosi', 'renovaciones_automaticas')
    )
    
    alertas: List[AlertaRenovacionAutomatica] = []
    
    for contrato in contratos_vigentes:
        # Obtener la fecha final actual del contrato sin considerar renovaciones futuras
        fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_base)
        
        # Verificar si el contrato ya tiene una renovación automática aprobada
        # Si la tiene, significa que ya fue gestionada y no debe aparecer en las alertas pendientes
        renovacion_aprobada = RenovacionAutomatica.objects.filter(
            contrato=contrato,
            estado='APROBADO'
        ).order_by('-fecha_aprobacion', '-effective_from', '-version').first()
        
        # Si existe una renovación aprobada, verificar si ya gestionó este contrato
        if renovacion_aprobada:
            # Si la renovación tiene effective_from y es posterior a la fecha final actual,
            # significa que ya está gestionada para el período siguiente (renovación futura aprobada)
            if renovacion_aprobada.effective_from and fecha_final_actual:
                # Si la renovación inicia después de la fecha final actual, ya está gestionado
                if renovacion_aprobada.effective_from > fecha_final_actual:
                    continue
                # Si la renovación ya está vigente (effective_from <= fecha_base), también está gestionado
                elif renovacion_aprobada.effective_from <= fecha_base:
                    continue
            # Si no tiene effective_from pero tiene nueva_fecha_final_actualizada y está aprobada,
            # verificar si extiende más allá de la ventana de alerta
            elif renovacion_aprobada.nueva_fecha_final_actualizada:
                if renovacion_aprobada.nueva_fecha_final_actualizada > fecha_limite:
                    continue
        
        
        if not fecha_final_actual:
            continue
        
        fecha_inicial = contrato.fecha_inicial_contrato
        if fecha_inicial and fecha_inicial > fecha_base:
            continue
        
        if fecha_final_actual < fecha_base:
            dias_restantes = 0
        else:
            dias_restantes = (fecha_final_actual - fecha_base).days
        
        if fecha_final_actual <= fecha_limite:
            otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
                contrato, 'nueva_fecha_final_actualizada', fecha_base
            )
            otrosi_modificador_numero = obtener_numero_evento(otrosi_modificador)
            
            alertas.append(
                AlertaRenovacionAutomatica(
                    contrato=contrato,
                    fecha_final_actualizada=fecha_final_actual,
                    dias_restantes=dias_restantes,
                    duracion_inicial_meses=contrato.duracion_inicial_meses,
                    otrosi_modificador=otrosi_modificador_numero,
                )
            )
    
    return sorted(
        alertas,
        key=lambda alerta: (
            alerta.dias_restantes,
            alerta.contrato.num_contrato,
        ),
    )

