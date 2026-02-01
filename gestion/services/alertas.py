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
    
    try:
        # Intentar obtener numero_otrosi primero
        if hasattr(evento, 'numero_otrosi'):
            numero = getattr(evento, 'numero_otrosi', None)
            if numero and str(numero).strip() and str(numero) != 'OS-TEMP':
                return str(numero).strip()
        
        # Intentar obtener numero_renovacion
        if hasattr(evento, 'numero_renovacion'):
            numero = getattr(evento, 'numero_renovacion', None)
            if numero and str(numero).strip() and str(numero) != 'RA-TEMP':
                return str(numero).strip()
        
        # Si no se encontró número válido, intentar obtener el ID como fallback
        if hasattr(evento, 'id'):
            evento_id = getattr(evento, 'id', None)
            if evento_id:
                # Determinar el tipo de evento
                if hasattr(evento, 'numero_otrosi'):
                    return f'OS-{evento_id}'
                elif hasattr(evento, 'numero_renovacion'):
                    return f'RA-{evento_id}'
        
        return None
    except Exception:
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
    Obtiene la fecha final actualizada de un contrato considerando Otrosí y Renovaciones Automáticas vigentes.
    
    Args:
        contrato: Contrato del cual obtener la fecha final.
        fecha_referencia: Fecha de referencia para evaluar eventos vigentes.
    
    Returns:
        Fecha final actualizada o None si no existe.
    """
    from gestion.models import RenovacionAutomatica
    from gestion.utils_otrosi import get_otrosi_vigente
    
    # Primero verificar si hay una Renovación Automática vigente (tiene prioridad)
    renovacion_vigente = RenovacionAutomatica.objects.filter(
        contrato=contrato,
        estado='APROBADO',
        effective_from__lte=fecha_referencia
    ).filter(
        Q(effective_to__gte=fecha_referencia) | Q(effective_to__isnull=True)
    ).order_by('-effective_from', '-fecha_aprobacion', '-version').first()
    
    if renovacion_vigente and renovacion_vigente.nueva_fecha_final_actualizada:
        return renovacion_vigente.nueva_fecha_final_actualizada
    
    # Si no hay renovación vigente, verificar Otro Sí vigente
    otrosi_vigente_actual = get_otrosi_vigente(contrato, fecha_referencia)
    
    if otrosi_vigente_actual:
        # Si tiene effective_to, esa es la fecha final vigente
        if otrosi_vigente_actual.effective_to:
            return otrosi_vigente_actual.effective_to
        # Si no tiene effective_to pero tiene nueva_fecha_final_actualizada, usar esa
        elif otrosi_vigente_actual.nueva_fecha_final_actualizada:
            return otrosi_vigente_actual.nueva_fecha_final_actualizada
    
    # Si no hay Otro Sí vigente, usar efecto cadena para obtener fecha final vigente hasta fecha_referencia
    otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato, 'nueva_fecha_final_actualizada', fecha_referencia
    )
    if otrosi_modificador and otrosi_modificador.nueva_fecha_final_actualizada:
        return otrosi_modificador.nueva_fecha_final_actualizada
    
    # Si no hay modificaciones, usar fecha_final_actualizada del contrato si existe, sino fecha_final_inicial
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
        .prefetch_related('otrosi', 'renovaciones_automaticas')
    )
    
    if tipo_contrato_cp:
        contratos_vigentes = contratos_vigentes.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cp)
    
    alertas_con_fecha = []
    for contrato in contratos_vigentes:
        try:
            # Obtener la fecha final actualizada usando efecto cadena (considera Otrosí y Renovaciones Automáticas vigentes)
            fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_base)
            
            if fecha_final_actual and fecha_base <= fecha_final_actual <= fecha_limite:
                alertas_con_fecha.append((contrato, fecha_final_actual))
        except Exception:
            # Si hay error al obtener la fecha final, continuar con el siguiente contrato
            continue
    
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
            
        # Procesar si tiene periodicidad ANUAL o FECHA_ESPECIFICA
        if periodicidad_ipc not in ['ANUAL', 'FECHA_ESPECIFICA']:
            continue
        
        # Calcular la próxima fecha de aumento usando la función utilitaria
        # que considera el último cálculo realizado y calcula correctamente
        from gestion.utils_ipc import calcular_proxima_fecha_aumento
        fecha_aumento_anual = calcular_proxima_fecha_aumento(contrato, fecha_base)
        
        # Si no se puede calcular la fecha, continuar con el siguiente contrato
        if not fecha_aumento_anual:
            continue
        
        # Verificar si ya tiene cálculo para esta fecha exacta
        # Los cálculos eliminados se borran físicamente de la base de datos
        calculo_existente = CalculoIPC.objects.filter(
            contrato=contrato,
            fecha_aplicacion=fecha_aumento_anual
        ).exists()
        
        # Si ya tiene cálculo, no mostrar la alerta
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
        
        # Si no hay modificador de IPC pero hay una renovación reciente que podría estar causando la alerta,
        # buscar renovaciones (OtroSi RENEWAL o RenovacionAutomatica) que no modificaron IPC
        if not otrosi_modificador_numero:
            try:
                from gestion.models import OtroSi, RenovacionAutomatica
                
                # Buscar último cálculo para comparar con renovaciones
                ultimo_calculo_ipc = CalculoIPC.objects.filter(
                    contrato=contrato
                ).order_by('-fecha_aplicacion', '-fecha_calculo').first()
                
                fecha_ultimo_calculo = ultimo_calculo_ipc.fecha_aplicacion if ultimo_calculo_ipc else None
                
                # Buscar renovaciones OtroSi tipo RENEWAL que no modificaron IPC
                renovacion_otrosi = OtroSi.objects.filter(
                    contrato=contrato,
                    estado='APROBADO',
                    tipo='RENEWAL',
                    effective_from__lte=fecha_base
                ).exclude(
                    nuevo_tipo_condicion_ipc__isnull=False
                ).exclude(
                    nueva_periodicidad_ipc__isnull=False
                ).exclude(
                    nueva_fecha_aumento_ipc__isnull=False
                ).order_by('-effective_from', '-version').first()
                
                # Buscar Renovaciones Automáticas
                renovacion_automatica = RenovacionAutomatica.objects.filter(
                    contrato=contrato,
                    estado='APROBADO',
                    effective_from__lte=fecha_base
                ).order_by('-effective_from', '-version').first()
                
                # Determinar cuál renovación es más reciente y si es posterior al último cálculo
                renovacion_relevante = None
                if renovacion_otrosi and renovacion_automatica:
                    if (hasattr(renovacion_otrosi, 'effective_from') and renovacion_otrosi.effective_from and
                        hasattr(renovacion_automatica, 'effective_from') and renovacion_automatica.effective_from):
                        renovacion_relevante = renovacion_otrosi if renovacion_otrosi.effective_from >= renovacion_automatica.effective_from else renovacion_automatica
                elif renovacion_otrosi and hasattr(renovacion_otrosi, 'effective_from') and renovacion_otrosi.effective_from:
                    renovacion_relevante = renovacion_otrosi
                elif renovacion_automatica and hasattr(renovacion_automatica, 'effective_from') and renovacion_automatica.effective_from:
                    renovacion_relevante = renovacion_automatica
                
                # Si hay renovación relevante y (no hay último cálculo o la renovación es posterior al último cálculo),
                # usar la renovación como modificador
                if renovacion_relevante and hasattr(renovacion_relevante, 'effective_from') and renovacion_relevante.effective_from:
                    if not fecha_ultimo_calculo or renovacion_relevante.effective_from > fecha_ultimo_calculo:
                        otrosi_modificador_numero = obtener_numero_evento(renovacion_relevante)
            except Exception:
                # Si hay algún error al buscar renovaciones, continuar sin modificador
                pass

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
        
        # Calcular la próxima fecha de aumento usando la función utilitaria
        # que considera el último cálculo realizado y calcula correctamente
        from gestion.utils_ipc import calcular_proxima_fecha_aumento
        fecha_aumento_anual = calcular_proxima_fecha_aumento(contrato, fecha_base)
        
        # Si no se puede calcular la fecha, continuar con el siguiente contrato
        if not fecha_aumento_anual:
            continue
        
        # Verificar si ya tiene cálculo para esta fecha exacta
        # Los cálculos eliminados se borran físicamente de la base de datos
        calculo_existente = CalculoSalarioMinimo.objects.filter(
            contrato=contrato,
            fecha_aplicacion=fecha_aumento_anual
        ).exists()
        
        # Si ya tiene cálculo, no mostrar la alerta
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
        
        # Si no hay modificador pero hay una renovación reciente que podría estar causando la alerta,
        # buscar renovaciones (OtroSi RENEWAL o RenovacionAutomatica) que no modificaron condiciones
        if not otrosi_modificador_numero:
            try:
                from gestion.models import OtroSi, RenovacionAutomatica
                
                # Buscar último cálculo para comparar con renovaciones
                ultimo_calculo_sm = CalculoSalarioMinimo.objects.filter(
                    contrato=contrato
                ).order_by('-fecha_aplicacion', '-fecha_calculo').first()
                
                fecha_ultimo_calculo = ultimo_calculo_sm.fecha_aplicacion if ultimo_calculo_sm else None
                
                # Buscar renovaciones OtroSi tipo RENEWAL que no modificaron condiciones
                renovacion_otrosi = OtroSi.objects.filter(
                    contrato=contrato,
                    estado='APROBADO',
                    tipo='RENEWAL',
                    effective_from__lte=fecha_base
                ).exclude(
                    nuevo_tipo_condicion_ipc__isnull=False
                ).exclude(
                    nueva_periodicidad_ipc__isnull=False
                ).exclude(
                    nueva_fecha_aumento_ipc__isnull=False
                ).order_by('-effective_from', '-version').first()
                
                # Buscar Renovaciones Automáticas
                renovacion_automatica = RenovacionAutomatica.objects.filter(
                    contrato=contrato,
                    estado='APROBADO',
                    effective_from__lte=fecha_base
                ).order_by('-effective_from', '-version').first()
                
                # Determinar cuál renovación es más reciente y si es posterior al último cálculo
                renovacion_relevante = None
                if renovacion_otrosi and renovacion_automatica:
                    if (hasattr(renovacion_otrosi, 'effective_from') and renovacion_otrosi.effective_from and
                        hasattr(renovacion_automatica, 'effective_from') and renovacion_automatica.effective_from):
                        renovacion_relevante = renovacion_otrosi if renovacion_otrosi.effective_from >= renovacion_automatica.effective_from else renovacion_automatica
                elif renovacion_otrosi and hasattr(renovacion_otrosi, 'effective_from') and renovacion_otrosi.effective_from:
                    renovacion_relevante = renovacion_otrosi
                elif renovacion_automatica and hasattr(renovacion_automatica, 'effective_from') and renovacion_automatica.effective_from:
                    renovacion_relevante = renovacion_automatica
                
                # Si hay renovación relevante y (no hay último cálculo o la renovación es posterior al último cálculo),
                # usar la renovación como modificador
                if renovacion_relevante and hasattr(renovacion_relevante, 'effective_from') and renovacion_relevante.effective_from:
                    if not fecha_ultimo_calculo or renovacion_relevante.effective_from > fecha_ultimo_calculo:
                        otrosi_modificador_numero = obtener_numero_evento(renovacion_relevante)
            except Exception:
                # Si hay algún error al buscar renovaciones, continuar sin modificador
                pass

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
    Solo incluye pólizas de contratos vigentes (verificado por fechas considerando renovaciones y Otrosí).

    Args:
        fecha_referencia: Fecha base para evaluar vencimientos.
        ventana_dias: Ventana de evaluación para las vigencias próximas.
        tipo_contrato_cp: Filtro opcional por tipo de contrato (CLIENTE/PROVEEDOR).
    
    Returns:
        Lista de pólizas críticas ordenadas por fecha de vencimiento.
    """
    from gestion.utils_otrosi import get_otrosi_vigente
    
    fecha_base = fecha_referencia or timezone.now().date()
    fecha_limite = fecha_base + timedelta(days=ventana_dias)
    
    # Obtener todas las pólizas que cumplen los criterios de fecha
    # Incluir pólizas vencidas o que vencen dentro de la ventana
    # Nota: El filtro inicial usa fecha_vencimiento, pero luego verificamos fecha_vencimiento_real si tiene colchón
    polizas_candidatas = (
        Poliza.objects.filter(
            fecha_vencimiento__isnull=False,
            fecha_vencimiento__lte=fecha_limite
        )
        .select_related('contrato', 'contrato__arrendatario', 'contrato__proveedor')
        .prefetch_related('contrato__otrosi', 'contrato__renovaciones_automaticas')
        .order_by('fecha_vencimiento')
    )
    
    # Intentar agregar select_related para otrosi y renovacion_automatica si existen
    try:
        # Verificar si los campos existen en el modelo
        if hasattr(Poliza, 'otrosi') and hasattr(Poliza, 'renovacion_automatica'):
            polizas_candidatas = polizas_candidatas.select_related('otrosi', 'renovacion_automatica')
    except Exception:
        # Si hay error, continuar sin select_related para esos campos
        pass
    
    if tipo_contrato_cp:
        polizas_candidatas = polizas_candidatas.filter(contrato__tipo_contrato_cliente_proveedor=tipo_contrato_cp)
    
    # Filtrar solo las de contratos vigentes (verificado por fechas considerando renovaciones)
    polizas_criticas = []
    for poliza in polizas_candidatas:
        contrato = poliza.contrato
        
        try:
            # Verificar vigencia basándose en fechas, no solo en el campo booleano
            # Considerar Otrosí y Renovaciones Automáticas que puedan haber modificado la fecha final
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
            
            # Usar fecha de vencimiento efectiva (considerando colchón si aplica)
            fecha_vencimiento_efectiva = poliza.obtener_fecha_vencimiento_efectiva(fecha_base)
            
            # Verificar que la póliza realmente vence dentro de la ventana o ya venció
            # Esto asegura que solo mostramos pólizas que realmente necesitan atención
            dias_para_vencer = (fecha_vencimiento_efectiva - fecha_base).days
            
            # Incluir pólizas vencidas o que vencen dentro de la ventana
            if dias_para_vencer <= ventana_dias:
                polizas_criticas.append(poliza)
        except Exception:
            # Si hay algún error al verificar la vigencia, continuar con la siguiente póliza
            # Esto evita que errores en un contrato afecten a otros
            continue
    
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
        .prefetch_related('otrosi', 'renovaciones_automaticas')
    )
    
    if tipo_contrato_cp:
        contratos_vigentes = contratos_vigentes.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cp)
    
    alertas_con_fecha = []
    for contrato in contratos_vigentes:
        try:
            # Obtener la fecha final actualizada usando efecto cadena (considera Otrosí y Renovaciones Automáticas vigentes)
            fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_base)
            
            # Usar prórroga automática del contrato (no existe campo en OtroSi para esto)
            prorroga_automatica = contrato.prorroga_automatica
            
            if fecha_final_actual and fecha_final_actual <= fecha_limite and not prorroga_automatica:
                alertas_con_fecha.append((contrato, fecha_final_actual))
        except Exception:
            # Si hay error al obtener la fecha final, continuar con el siguiente contrato
            continue
    
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
        .prefetch_related('otrosi', 'renovaciones_automaticas', 'polizas')
    )
    
    if tipo_contrato_cp:
        contratos_vigentes = contratos_vigentes.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cp)
    
    alertas: List[AlertaPolizaRequerida] = []
    
    for contrato in contratos_vigentes:
        try:
            # Verificar que el contrato esté vigente por fechas (considerando renovaciones y Otrosí)
            fecha_final_contrato = _obtener_fecha_final_contrato(contrato, fecha_base)
            fecha_inicial = contrato.fecha_inicial_contrato
            
            if fecha_inicial and fecha_inicial > fecha_base:
                continue
            
            if fecha_final_contrato and fecha_final_contrato < fecha_base:
                continue
        except Exception:
            # Si hay error al verificar la vigencia, continuar con el siguiente contrato
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
        .prefetch_related('otrosi', 'renovaciones_automaticas')
    )
    
    if tipo_contrato_cp:
        contratos_vigentes = contratos_vigentes.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cp)
    
    alertas: List[AlertaTerminacionAnticipada] = []
    
    for contrato in contratos_vigentes:
        try:
            # Obtener la fecha final actualizada usando efecto cadena (considerando renovaciones y Otrosí)
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
                
                # Determinar qué Otrosí o Renovación Automática modificó la fecha final
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
        except Exception:
            # Si hay error al procesar el contrato, continuar con el siguiente
            continue
    
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
        try:
            # Obtener la fecha final actual del contrato considerando renovaciones y Otrosí vigentes
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
        except Exception:
            # Si hay error al procesar el contrato, continuar con el siguiente
            continue
    
    return sorted(
        alertas,
        key=lambda alerta: (
            alerta.dias_restantes,
            alerta.contrato.num_contrato,
        ),
    )

