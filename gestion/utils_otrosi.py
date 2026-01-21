"""
Utilidades para gestión de Otrosí y vistas vigentes de contratos
"""
from datetime import date
from decimal import Decimal
from django.db.models import Q


def _obtener_numero_evento(evento):
    """Retorna el número del evento (Otro Sí o Renovación Automática)."""
    if not evento:
        return None
    if hasattr(evento, 'numero_otrosi'):
        return evento.numero_otrosi
    if hasattr(evento, 'numero_renovacion'):
        return evento.numero_renovacion
    return str(evento)


def _obtener_label_evento(evento):
    """Retorna una etiqueta legible del evento."""
    if not evento:
        return 'Evento'
    if hasattr(evento, 'numero_otrosi'):
        return f'Otro Sí {evento.numero_otrosi}'
    if hasattr(evento, 'numero_renovacion'):
        return f'Renovación Automática {evento.numero_renovacion}'
    return str(evento)


def es_fecha_fuera_vigencia_contrato(contrato, fecha_referencia):
    """
    Determina si una fecha es anterior al inicio del contrato.
    """
    fecha_inicio = getattr(contrato, 'fecha_inicial_contrato', None)
    if not fecha_inicio or not fecha_referencia:
        return False
    return fecha_referencia < fecha_inicio


def tiene_otrosi_posteriores(otrosi):
    """
    Verifica si hay Otros Sí posteriores al Otro Sí dado.
    
    Un Otro Sí es "posterior" si tiene un número mayor que el Otro Sí actual.
    Por ejemplo, si el Otro Sí actual es "OS-1", un Otro Sí con "OS-2" sería posterior.
    
    Args:
        otrosi: Instancia del modelo OtroSi
        
    Returns:
        bool: True si hay Otros Sí posteriores, False en caso contrario
    """
    if not otrosi or not otrosi.numero_otrosi:
        return False
    
    # Extraer el número del Otro Sí actual (ej: "OS-1" -> 1)
    try:
        numero_actual = int(otrosi.numero_otrosi.split('-')[1])
    except (ValueError, IndexError):
        # Si no se puede parsear, asumir que no hay posteriores
        return False
    
    # Buscar Otros Sí del mismo contrato con número mayor
    otrosi_posteriores = otrosi.contrato.otrosi.filter(
        numero_otrosi__regex=r'^OS-\d+$'
    ).exclude(id=otrosi.id)
    
    for otro in otrosi_posteriores:
        try:
            numero_otro = int(otro.numero_otrosi.split('-')[1])
            if numero_otro > numero_actual:
                return True
        except (ValueError, IndexError):
            continue
    
    return False


def get_ultimo_otrosi_aprobado(contrato):
    """
    Obtiene el último Otrosí aprobado para un contrato, sin importar si está vigente.
    
    Reglas:
    - Estado APROBADO
    - Ordenado por fecha de aprobación descendente, luego por effective_from descendente
    """
    from .models import OtroSi
    
    ultimo_otrosi = OtroSi.objects.filter(
        contrato=contrato,
        estado='APROBADO'
    ).order_by('-fecha_aprobacion', '-effective_from', '-version').first()
    
    return ultimo_otrosi


def get_ultimo_otrosi_que_modifico_campo(contrato, campo_nombre):
    """
    Obtiene el último Otrosí o Renovación Automática aprobado que modificó un campo específico.
    
    Busca en orden cronológico descendente (más reciente primero) el último evento
    que tiene un valor no nulo/no vacío en el campo especificado.
    
    Args:
        contrato: Instancia del modelo Contrato
        campo_nombre: Nombre del campo en el modelo OtroSi/RenovacionAutomatica (ej: 'nuevo_valor_canon')
    
    Returns:
        OtroSi, RenovacionAutomatica o None si ningún evento modificó ese campo
    """
    from .models import OtroSi, RenovacionAutomatica
    from django.utils import timezone
    
    # Obtener todos los Otros Sí aprobados ordenados por fecha de aprobación descendente
    otrosis_aprobados = OtroSi.objects.filter(
        contrato=contrato,
        estado='APROBADO'
    ).order_by('-fecha_aprobacion', '-effective_from', '-version')
    
    # Obtener todas las Renovaciones Automáticas aprobadas ordenadas por fecha de aprobación descendente
    renovaciones_aprobadas = RenovacionAutomatica.objects.filter(
        contrato=contrato,
        estado='APROBADO'
    ).order_by('-fecha_aprobacion', '-effective_from', '-version')
    
    # Combinar y ordenar por fecha de aprobación descendente
    eventos = []
    for otrosi in otrosis_aprobados:
        eventos.append(('otrosi', otrosi))
    for renovacion in renovaciones_aprobadas:
        eventos.append(('renovacion', renovacion))
    
    # Ordenar por effective_from descendente (más reciente primero), luego por fecha_aprobacion descendente
    # Esto asegura que se tome el Otro Sí más reciente en vigencia, no el más recientemente aprobado
    eventos.sort(key=lambda x: (
        x[1].effective_from,
        x[1].fecha_aprobacion if x[1].fecha_aprobacion else timezone.now(),
        -x[1].version if hasattr(x[1], 'version') else 0
    ), reverse=True)
    
    # Buscar el primero que tenga el campo modificado (no None y no vacío)
    for tipo_evento, evento in eventos:
        valor = getattr(evento, campo_nombre, None)
        # Verificar si el campo tiene un valor válido
        if valor is not None:
            # Para strings, verificar que no esté vacío
            if isinstance(valor, str) and valor.strip() != '':
                return evento
            # Para otros tipos (Decimal, int, bool, date), si no es None, es válido
            elif not isinstance(valor, str):
                return evento
    
    return None


def get_ultimo_otrosi_que_modifico_campo_hasta_fecha(contrato, campo_nombre, fecha_referencia, permitir_futuros=False):
    """
    Obtiene el último Otrosí o Renovación Automática aprobado que modificó un campo específico hasta una fecha de referencia.
    
    Implementa el efecto cadena: busca el último Otro Sí o Renovación Automática que modificó el campo
    ANTES O EN la fecha de referencia, respetando las fechas de vigencia.
    
    Args:
        contrato: Instancia del modelo Contrato
        campo_nombre: Nombre del campo en el modelo OtroSi/RenovacionAutomatica (ej: 'nuevo_valor_canon')
        fecha_referencia: Fecha hasta la cual buscar (datetime.date)
        permitir_futuros: Si es True, considera también eventos con effective_from en el futuro.
                         Útil para gestionar pólizas antes del inicio del contrato.
    
    Returns:
        OtroSi, RenovacionAutomatica o None si ningún evento modificó ese campo hasta esa fecha
    """
    from .models import OtroSi, RenovacionAutomatica
    from django.utils import timezone
    
    if fecha_referencia is None:
        fecha_referencia = date.today()
    
    # Obtener eventos de ambos tipos
    eventos = []
    
    # Si permitir_futuros es True, no filtrar por effective_from
    if permitir_futuros:
        otrosis_aprobados = OtroSi.objects.filter(
            contrato=contrato,
            estado='APROBADO'
        ).order_by('-effective_from', '-fecha_aprobacion', '-version')
        
        renovaciones_aprobadas = RenovacionAutomatica.objects.filter(
            contrato=contrato,
            estado='APROBADO'
        ).order_by('-effective_from', '-fecha_aprobacion', '-version')
    else:
        # Obtener todos los eventos aprobados que sean vigentes hasta la fecha de referencia
        otrosis_aprobados = OtroSi.objects.filter(
            contrato=contrato,
            estado='APROBADO',
            effective_from__lte=fecha_referencia
        ).order_by('-effective_from', '-fecha_aprobacion', '-version')
        
        renovaciones_aprobadas = RenovacionAutomatica.objects.filter(
            contrato=contrato,
            estado='APROBADO',
            effective_from__lte=fecha_referencia
        ).order_by('-effective_from', '-fecha_aprobacion', '-version')
    
    # Combinar eventos
    # Para pólizas, incluimos todos los eventos que hayan iniciado antes o en la fecha de referencia
    # Si permitir_futuros es True, también incluimos eventos con fechas futuras
    # Esto asegura que si un Otro Sí venció pero fue el último que modificó los campos, lo consideremos
    for otrosi in otrosis_aprobados:
        # Si permitir_futuros es True, incluir todos los OtroSí aprobados (incluso con fechas futuras)
        # Si no, solo incluir los que iniciaron antes o en la fecha de referencia
        if permitir_futuros or otrosi.effective_from <= fecha_referencia:
            eventos.append(('otrosi', otrosi))
    
    for renovacion in renovaciones_aprobadas:
        # Si permitir_futuros es True, incluir todas las renovaciones aprobadas (incluso con fechas futuras)
        # Si no, solo incluir las que iniciaron antes o en la fecha de referencia
        if permitir_futuros or renovacion.effective_from <= fecha_referencia:
            eventos.append(('renovacion', renovacion))
    
    # Ordenar por effective_from descendente (más reciente primero), luego por fecha_aprobacion descendente
    # Esto asegura que se tome el Otro Sí más reciente en vigencia, no el más recientemente aprobado
    eventos.sort(key=lambda x: (
        x[1].effective_from,
        x[1].fecha_aprobacion if x[1].fecha_aprobacion else timezone.now(),
        -x[1].version if hasattr(x[1], 'version') else 0
    ), reverse=True)
    
    # Buscar el primero que tenga el campo modificado (no None y no vacío)
    # y que sea vigente en la fecha de referencia
    for tipo_evento, evento in eventos:
        # Verificar que el evento sea vigente en la fecha de referencia
        # Un evento es vigente si su effective_from <= fecha_referencia
        # y (effective_to >= fecha_referencia o effective_to es None)
        es_vigente = evento.effective_from <= fecha_referencia
        if evento.effective_to is not None:
            es_vigente = es_vigente and evento.effective_to >= fecha_referencia
        
        if not es_vigente:
            continue
        
        valor = getattr(evento, campo_nombre, None)
        # Verificar si el campo tiene un valor válido
        if valor is not None:
            # Para strings, verificar que no esté vacío
            if isinstance(valor, str) and valor.strip() != '':
                return evento
            # Para otros tipos (Decimal, int, bool, date), si no es None, es válido
            elif not isinstance(valor, str):
                return evento
    
    return None


def get_otrosi_vigente(contrato, fecha_referencia=None):
    """
    Obtiene el Otrosí o Renovación Automática vigente para un contrato en una fecha dada.
    
    Reglas:
    - Estado APROBADO
    - effective_from <= fecha_referencia
    - effective_to >= fecha_referencia (o null)
    - Mayor versión en caso de empate
    - Prioriza OtroSi sobre RenovacionAutomatica si ambos están vigentes
    """
    if fecha_referencia is None:
        fecha_referencia = date.today()
    
    # Importar aquí para evitar circular import
    from .models import OtroSi, RenovacionAutomatica
    
    otrosis_vigentes = OtroSi.objects.filter(
        contrato=contrato,
        estado='APROBADO',
        effective_from__lte=fecha_referencia
    ).filter(
        Q(effective_to__gte=fecha_referencia) | Q(effective_to__isnull=True)
    ).order_by('-effective_from', '-version')
    
    # Si hay un OtroSi vigente, retornarlo (tiene prioridad)
    otrosi_vigente = otrosis_vigentes.first()
    if otrosi_vigente:
        return otrosi_vigente
    
    # Si no hay OtroSi vigente, buscar Renovación Automática vigente
    renovaciones_vigentes = RenovacionAutomatica.objects.filter(
        contrato=contrato,
        estado='APROBADO',
        effective_from__lte=fecha_referencia
    ).filter(
        Q(effective_to__gte=fecha_referencia) | Q(effective_to__isnull=True)
    ).order_by('-effective_from', '-version')
    
    return renovaciones_vigentes.first()


def get_vista_vigente_contrato(contrato, fecha_referencia=None):
    """
    Obtiene la "vista vigente" del contrato aplicando el efecto cadena.
    
    Para cada campo, busca el último Otro Sí que lo modificó hasta la fecha de referencia.
    Si ningún Otro Sí lo modificó, usa el valor del contrato base.
    
    Retorna un diccionario con:
    - Los valores del contrato base o del último Otro Sí que los modificó hasta la fecha
    - Metadata adicional de qué fue modificado y por qué Otro Sí
    """
    if fecha_referencia is None:
        fecha_referencia = date.today()

    if es_fecha_fuera_vigencia_contrato(contrato, fecha_referencia):
        return {
            'contrato': contrato,
            'num_contrato': contrato.num_contrato,
            'fecha_referencia': fecha_referencia,
            'otrosi_vigente': None,
            'campos_modificados': {},
            'tiene_modificaciones': False,
            'vista_disponible': False,
            'mensaje_sin_vigencia': (
                f'La fecha {fecha_referencia} es anterior al inicio del contrato '
                f'({contrato.fecha_inicial_contrato}).'
            ),
        }
    
    # Función auxiliar para obtener valor de un campo con efecto cadena
    def obtener_valor_campo(campo_otrosi, campo_contrato, tipo='valor'):
        """
        Obtiene el valor de un campo usando efecto cadena.
        
        Args:
            campo_otrosi: Nombre del campo en OtroSi (ej: 'nuevo_valor_canon')
            campo_contrato: Nombre del campo en Contrato (ej: 'valor_canon_fijo')
            tipo: 'valor', 'bool', 'fecha'
        """
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, campo_otrosi, fecha_referencia
        )
        
        if otrosi_modificador:
            valor = getattr(otrosi_modificador, campo_otrosi, None)
            if valor is not None:
                # Para strings, verificar que no esté vacío
                if isinstance(valor, str) and valor.strip() != '':
                    return valor, otrosi_modificador
                # Para otros tipos, si no es None, es válido
                elif not isinstance(valor, str):
                    return valor, otrosi_modificador
        
        # Si no hay Otro Sí que lo modificó, usar valor del contrato
        valor_contrato = getattr(contrato, campo_contrato, None)
        return valor_contrato, None
    
    # Vista base del contrato
    vista = {
        # Datos base
        'contrato': contrato,
        'num_contrato': contrato.num_contrato,
        'fecha_referencia': fecha_referencia,
        
        # Metadata
        'otrosi_vigente': get_otrosi_vigente(contrato, fecha_referencia),
        'campos_modificados': {},
        'tiene_modificaciones': False,
        'vista_disponible': True,
        'mensaje_sin_vigencia': None,
    }
    
    # Obtener valores con efecto cadena para campos financieros
    valor_canon, otrosi_canon = obtener_valor_campo('nuevo_valor_canon', 'valor_canon_fijo')
    vista['valor_canon'] = valor_canon
    if otrosi_canon:
        vista['campos_modificados']['valor_canon'] = {
            'original': contrato.valor_canon_fijo,
            'nuevo': valor_canon,
            'otrosi': _obtener_numero_evento(otrosi_canon),
            'version': otrosi_canon.version
        }
        vista['tiene_modificaciones'] = True
    
    modalidad_pago, otrosi_modalidad = obtener_valor_campo('nueva_modalidad_pago', 'modalidad_pago')
    vista['modalidad_pago'] = modalidad_pago
    if otrosi_modalidad:
        vista['campos_modificados']['modalidad_pago'] = {
            'original': contrato.modalidad_pago,
            'nuevo': modalidad_pago,
            'otrosi': _obtener_numero_evento(otrosi_modalidad),
            'version': otrosi_modalidad.version
        }
        vista['tiene_modificaciones'] = True
    
    canon_minimo, otrosi_canon_min = obtener_valor_campo('nuevo_canon_minimo_garantizado', 'canon_minimo_garantizado')
    vista['canon_minimo_garantizado'] = canon_minimo
    if otrosi_canon_min:
        vista['campos_modificados']['canon_minimo_garantizado'] = {
            'original': contrato.canon_minimo_garantizado,
            'nuevo': canon_minimo,
            'otrosi': _obtener_numero_evento(otrosi_canon_min),
            'version': otrosi_canon_min.version
        }
        vista['tiene_modificaciones'] = True
    
    porcentaje_ventas, otrosi_ventas = obtener_valor_campo('nuevo_porcentaje_ventas', 'porcentaje_ventas')
    vista['porcentaje_ventas'] = porcentaje_ventas
    if otrosi_ventas:
        vista['campos_modificados']['porcentaje_ventas'] = {
            'original': contrato.porcentaje_ventas,
            'nuevo': porcentaje_ventas,
            'otrosi': _obtener_numero_evento(otrosi_ventas),
            'version': otrosi_ventas.version
        }
        vista['tiene_modificaciones'] = True
    
    # Plazo
    # Si hay un Otro Sí vigente con effective_to, usar ese valor como fecha final
    otrosi_vigente = vista.get('otrosi_vigente')
    fecha_final = None
    otrosi_fecha_final = None
    
    if otrosi_vigente:
        # Si el Otro Sí vigente tiene effective_to, usar ese valor (es la fecha final del contrato durante ese período)
        if otrosi_vigente.effective_to:
            fecha_final = otrosi_vigente.effective_to
            otrosi_fecha_final = otrosi_vigente
        # Si no tiene effective_to pero tiene nueva_fecha_final_actualizada, usar ese
        elif otrosi_vigente.nueva_fecha_final_actualizada:
            fecha_final = otrosi_vigente.nueva_fecha_final_actualizada
            otrosi_fecha_final = otrosi_vigente
    
    # Si no hay Otro Sí vigente o no tiene fecha final, buscar el último que modificó el campo
    if not fecha_final:
        fecha_final, otrosi_fecha_final = obtener_valor_campo('nueva_fecha_final_actualizada', 'fecha_final_actualizada')
        if fecha_final is None:
            fecha_final = contrato.fecha_final_inicial
    
    vista['fecha_final_actualizada'] = fecha_final
    if otrosi_fecha_final:
        vista['campos_modificados']['fecha_final_actualizada'] = {
            'original': contrato.fecha_final_actualizada or contrato.fecha_final_inicial,
            'nuevo': fecha_final,
            'otrosi': _obtener_numero_evento(otrosi_fecha_final),
            'version': otrosi_fecha_final.version
        }
        vista['tiene_modificaciones'] = True
    
    duracion_meses, otrosi_duracion = obtener_valor_campo('nuevo_plazo_meses', 'duracion_inicial_meses')
    vista['duracion_meses'] = duracion_meses
    if otrosi_duracion:
        vista['campos_modificados']['duracion_meses'] = {
            'original': contrato.duracion_inicial_meses,
            'nuevo': duracion_meses,
            'otrosi': _obtener_numero_evento(otrosi_duracion),
            'version': otrosi_duracion.version
        }
        vista['tiene_modificaciones'] = True
    
    # IPC
    tipo_ipc, otrosi_tipo_ipc = obtener_valor_campo('nuevo_tipo_condicion_ipc', 'tipo_condicion_ipc')
    vista['tipo_condicion_ipc'] = tipo_ipc
    if otrosi_tipo_ipc:
        vista['campos_modificados']['tipo_condicion_ipc'] = {
            'original': contrato.tipo_condicion_ipc,
            'nuevo': tipo_ipc,
            'otrosi': _obtener_numero_evento(otrosi_tipo_ipc),
            'version': otrosi_tipo_ipc.version
        }
        vista['tiene_modificaciones'] = True
    
    puntos_ipc, otrosi_puntos_ipc = obtener_valor_campo('nuevos_puntos_adicionales_ipc', 'puntos_adicionales_ipc')
    vista['puntos_adicionales_ipc'] = puntos_ipc
    if otrosi_puntos_ipc:
        vista['campos_modificados']['puntos_adicionales_ipc'] = {
            'original': contrato.puntos_adicionales_ipc,
            'nuevo': puntos_ipc,
            'otrosi': _obtener_numero_evento(otrosi_puntos_ipc),
            'version': otrosi_puntos_ipc.version
        }
        vista['tiene_modificaciones'] = True
    
    periodicidad_ipc, otrosi_periodicidad = obtener_valor_campo('nueva_periodicidad_ipc', 'periodicidad_ipc')
    vista['periodicidad_ipc'] = periodicidad_ipc
    if otrosi_periodicidad:
        vista['campos_modificados']['periodicidad_ipc'] = {
            'original': contrato.periodicidad_ipc,
            'nuevo': periodicidad_ipc,
            'otrosi': _obtener_numero_evento(otrosi_periodicidad),
            'version': otrosi_periodicidad.version
        }
        vista['tiene_modificaciones'] = True
    
    fecha_aumento_ipc, otrosi_fecha_ipc = obtener_valor_campo('nueva_fecha_aumento_ipc', 'fecha_aumento_ipc')
    vista['fecha_aumento_ipc'] = fecha_aumento_ipc
    if otrosi_fecha_ipc:
        vista['campos_modificados']['fecha_aumento_ipc'] = {
            'original': contrato.fecha_aumento_ipc,
            'nuevo': fecha_aumento_ipc,
            'otrosi': _obtener_numero_evento(otrosi_fecha_ipc),
            'version': otrosi_fecha_ipc.version
        }
        vista['tiene_modificaciones'] = True
    
    # Calcular fecha de aumento anual si la periodicidad es ANUAL
    fecha_aumento_anual = None
    fecha_aumento_anual_display = None
    
    if periodicidad_ipc == 'ANUAL' or contrato.periodicidad_ipc == 'ANUAL':
        # Si hay una nueva fecha de aumento IPC en el Otro Sí, usarla
        if fecha_aumento_ipc:
            fecha_aumento_anual = fecha_aumento_ipc
            fecha_aumento_anual_display = fecha_aumento_ipc.strftime('%d/%m/%Y') if fecha_aumento_ipc else None
        elif contrato.fecha_aumento_ipc:
            # Si el contrato tiene fecha de aumento IPC definida, usarla
            fecha_aumento_anual = contrato.fecha_aumento_ipc
            fecha_aumento_anual_display = contrato.fecha_aumento_ipc.strftime('%d/%m/%Y') if contrato.fecha_aumento_ipc else None
        else:
            # Por defecto, usar la fecha inicial del contrato
            if contrato.fecha_inicial_contrato:
                fecha_aumento_anual = contrato.fecha_inicial_contrato
                fecha_aumento_anual_display = contrato.fecha_inicial_contrato.strftime('%d/%m/%Y')
    
    vista['fecha_aumento_anual'] = fecha_aumento_anual
    vista['fecha_aumento_anual_display'] = fecha_aumento_anual_display
    
    return vista


def get_polizas_vigentes(contrato, fecha_referencia=None):
    """
    Obtiene las pólizas vigentes para un contrato, considerando Otrosí.
    
    Retorna las pólizas más recientes definidas por el Otrosí vigente;
    si no existen en Otrosí, usa las del contrato base.
    """
    if fecha_referencia is None:
        fecha_referencia = date.today()

    if es_fecha_fuera_vigencia_contrato(contrato, fecha_referencia):
        return contrato.polizas.none()
    
    # Importar aquí para evitar circular import
    from .models import Poliza
    
    # Buscar evento vigente (Otro Sí tiene prioridad sobre RA)
    otrosi_vigente = get_otrosi_vigente(contrato, fecha_referencia)
    
    if otrosi_vigente:
        # Solo es válido filtrar por el FK cuando el evento es un Otro Sí
        from .models import OtroSi  # import local para evitar circulares
        if isinstance(otrosi_vigente, OtroSi):
            polizas_otrosi = Poliza.objects.filter(
                otrosi=otrosi_vigente,
                fecha_vencimiento__gte=fecha_referencia
            )
            
            if polizas_otrosi.exists():
                # Si el Otro Sí tiene pólizas, retornarlas
                return polizas_otrosi
    
    # Si no hay Otro Sí vigente o no tiene pólizas, retornar del contrato base
    return contrato.polizas.filter(
        otrosi__isnull=True,
        fecha_vencimiento__gte=fecha_referencia
    )


def get_polizas_requeridas_contrato(contrato, fecha_referencia=None, permitir_fuera_vigencia=False):
    """
    Obtiene las pólizas requeridas aplicando el efecto cadena.
    
    Para cada campo de póliza, busca el último Otro Sí que lo modificó hasta la fecha de referencia.
    Si ningún Otro Sí lo modificó, usa el valor del contrato base.
    
    Args:
        contrato: Instancia del modelo Contrato
        fecha_referencia: Fecha de referencia para obtener valores vigentes (por defecto: hoy)
        permitir_fuera_vigencia: Si es True, permite obtener requisitos incluso si el contrato
                                 aún no ha iniciado o ya venció. Útil para gestionar pólizas
                                 antes del inicio del contrato.
    
    Retorna un diccionario con la configuración de cada tipo de póliza.
    """
    if fecha_referencia is None:
        fecha_referencia = date.today()

    if not permitir_fuera_vigencia and es_fecha_fuera_vigencia_contrato(contrato, fecha_referencia):
        return {}
    
    # Si permitir_fuera_vigencia es True, considerar también Otros Sí aprobados con fechas futuras
    # Esto permite gestionar pólizas que serán requeridas por OtroSí que aún no están vigentes
    considerar_futuros = permitir_fuera_vigencia
    
    # Función auxiliar para obtener valor con efecto cadena y el Otro Sí modificador
    def obtener_valor_y_otrosi(campo_otrosi, campo_contrato):
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, campo_otrosi, fecha_referencia, permitir_futuros=considerar_futuros
        )
        
        if otrosi_modificador:
            valor = getattr(otrosi_modificador, campo_otrosi, None)
            if valor is not None:
                # Para strings, verificar que no esté vacío
                if isinstance(valor, str) and valor.strip() != '':
                    return valor, otrosi_modificador
                # Para Decimal y otros tipos numéricos
                elif not isinstance(valor, str):
                    # Si el valor es 0, verificar si el contrato base tiene un valor diferente
                    # Si el contrato tiene un valor > 0, entonces 0 en el Otro Sí podría ser un valor por defecto
                    # y deberíamos usar el valor del contrato en su lugar
                    from decimal import Decimal
                    valor_contrato = getattr(contrato, campo_contrato, None)
                    if isinstance(valor, Decimal) and valor == Decimal('0') and valor_contrato and valor_contrato != Decimal('0'):
                        # El valor 0 podría ser un valor por defecto, usar el valor del contrato
                        return valor_contrato, None
                    # Para otros tipos o cuando el valor no es 0, retornar el valor del Otro Sí
                    return valor, otrosi_modificador
        
        # Si no hay Otro Sí que lo modificó, usar valor del contrato
        valor_contrato = getattr(contrato, campo_contrato, None)
        return valor_contrato, None
    
    # Función auxiliar para obtener valor con efecto cadena (mantener compatibilidad)
    def obtener_valor(campo_otrosi, campo_contrato):
        valor, _ = obtener_valor_y_otrosi(campo_otrosi, campo_contrato)
        return valor
    
    # Función auxiliar para obtener booleano con efecto cadena y el Otro Sí modificador
    def obtener_bool_y_otrosi(campo_otrosi, campo_contrato):
        # Solo buscar eventos que sean vigentes en la fecha de referencia
        # No permitir eventos futuros para asegurar que respetamos el estado histórico
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, campo_otrosi, fecha_referencia, permitir_futuros=False
        )
        
        if otrosi_modificador:
            # Verificar que el evento sea realmente vigente en la fecha de referencia
            # Un evento es vigente si su effective_from <= fecha_referencia
            # y (effective_to >= fecha_referencia o effective_to es None)
            # IMPORTANTE: Si effective_from > fecha_referencia, el evento NO es vigente
            if otrosi_modificador.effective_from > fecha_referencia:
                # El evento es futuro, no es vigente
                valor_contrato = getattr(contrato, campo_contrato, False)
                return valor_contrato, None
            
            es_vigente = otrosi_modificador.effective_from <= fecha_referencia
            if otrosi_modificador.effective_to is not None:
                es_vigente = es_vigente and otrosi_modificador.effective_to >= fecha_referencia
            
            if es_vigente:
                valor = getattr(otrosi_modificador, campo_otrosi, None)
                if valor is not None:
                    return bool(valor), otrosi_modificador
        
        # Si no hay Otro Sí que lo modificó o el evento no es vigente, usar valor del contrato
        valor_contrato = getattr(contrato, campo_contrato, False)
        return valor_contrato, None
    
    # Función auxiliar para obtener booleano con efecto cadena (mantener compatibilidad)
    def obtener_bool(campo_otrosi, campo_contrato):
        valor, _ = obtener_bool_y_otrosi(campo_otrosi, campo_contrato)
        return valor
    
    # Función auxiliar para obtener el identificador del modificador (OtroSi o RenovacionAutomatica)
    def obtener_identificador_modificador(modificador):
        """Obtiene el identificador del modificador (numero_otrosi o numero_renovacion)"""
        if not modificador:
            return None
        # Verificar si es OtroSi (tiene numero_otrosi)
        if hasattr(modificador, 'numero_otrosi'):
            return modificador.numero_otrosi
        # Verificar si es RenovacionAutomatica (tiene numero_renovacion)
        elif hasattr(modificador, 'numero_renovacion'):
            return modificador.numero_renovacion
        return None
    
    polizas_requeridas = {}
    
    # Póliza RCE
    exige_rce = obtener_bool('nuevo_exige_poliza_rce', 'exige_poliza_rce')
    if exige_rce:
        meses_rce = obtener_valor('nuevo_meses_vigencia_rce', 'meses_vigencia_rce')
        fecha_inicio_rce = obtener_valor('nuevo_fecha_inicio_vigencia_rce', 'fecha_inicio_vigencia_rce')
        fecha_fin_rce = obtener_valor('nuevo_fecha_fin_vigencia_rce', 'fecha_fin_vigencia_rce')
        
        # Si no hay fecha fin pero hay fecha inicio y meses, calcularla
        if not fecha_fin_rce and fecha_inicio_rce and meses_rce:
            from .utils import calcular_fecha_vencimiento
            fecha_fin_rce = calcular_fecha_vencimiento(fecha_inicio_rce, meses_rce)
        # Si no hay fecha inicio pero hay meses, usar fecha final del contrato
        elif not fecha_inicio_rce and meses_rce and contrato.fecha_final_actualizada:
            from .utils import calcular_fecha_vencimiento
            fecha_fin_rce = calcular_fecha_vencimiento(contrato.fecha_final_actualizada, meses_rce)
        
        detalles_rce = {
            'plo': obtener_valor('nuevo_valor_propietario_locatario_ocupante_rce', 'valor_propietario_locatario_ocupante_rce'),
            'patronal': obtener_valor('nuevo_valor_patronal_rce', 'valor_patronal_rce'),
            'gastos_medicos': obtener_valor('nuevo_valor_gastos_medicos_rce', 'valor_gastos_medicos_rce'),
            'vehiculos': obtener_valor('nuevo_valor_vehiculos_rce', 'valor_vehiculos_rce'),
            'contratistas': obtener_valor('nuevo_valor_contratistas_rce', 'valor_contratistas_rce'),
            'perjuicios': obtener_valor('nuevo_valor_perjuicios_extrapatrimoniales_rce', 'valor_perjuicios_extrapatrimoniales_rce'),
            'dano_moral': obtener_valor('nuevo_valor_dano_moral_rce', 'valor_dano_moral_rce'),
            'lucro_cesante': obtener_valor('nuevo_valor_lucro_cesante_rce', 'valor_lucro_cesante_rce'),
        }
        
        # Si es PROVEEDOR, agregar coberturas RCE específicas
        if contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR':
            detalles_rce.update({
                'danos_materiales': obtener_valor('nuevo_rce_cobertura_danos_materiales', 'rce_cobertura_danos_materiales'),
                'lesiones_personales': obtener_valor('nuevo_rce_cobertura_lesiones_personales', 'rce_cobertura_lesiones_personales'),
                'muerte_terceros': obtener_valor('nuevo_rce_cobertura_muerte_terceros', 'rce_cobertura_muerte_terceros'),
                'danos_bienes_terceros': obtener_valor('nuevo_rce_cobertura_danos_bienes_terceros', 'rce_cobertura_danos_bienes_terceros'),
                'responsabilidad_patronal': obtener_valor('nuevo_rce_cobertura_responsabilidad_patronal', 'rce_cobertura_responsabilidad_patronal'),
                'responsabilidad_cruzada': obtener_valor('nuevo_rce_cobertura_responsabilidad_cruzada', 'rce_cobertura_responsabilidad_cruzada'),
                'danos_contratistas': obtener_valor('nuevo_rce_cobertura_danos_contratistas', 'rce_cobertura_danos_contratistas'),
                'danos_ejecucion_contrato': obtener_valor('nuevo_rce_cobertura_danos_ejecucion_contrato', 'rce_cobertura_danos_ejecucion_contrato'),
                'danos_predios_vecinos': obtener_valor('nuevo_rce_cobertura_danos_predios_vecinos', 'rce_cobertura_danos_predios_vecinos'),
                'gastos_medicos_cobertura': obtener_valor('nuevo_rce_cobertura_gastos_medicos', 'rce_cobertura_gastos_medicos'),
                'gastos_defensa': obtener_valor('nuevo_rce_cobertura_gastos_defensa', 'rce_cobertura_gastos_defensa'),
                'perjuicios_patrimoniales': obtener_valor('nuevo_rce_cobertura_perjuicios_patrimoniales', 'rce_cobertura_perjuicios_patrimoniales'),
            })
        
        # Obtener el Otro Sí que modificó el valor principal para determinar la fuente
        valor_rce, otrosi_valor_rce = obtener_valor_y_otrosi('nuevo_valor_asegurado_rce', 'valor_asegurado_rce')
        otrosi_modificador_rce = otrosi_valor_rce
        
        polizas_requeridas['RCE - Responsabilidad Civil'] = {
            'tipo': 'RCE - Responsabilidad Civil',
            'valor_requerido': valor_rce,
            'meses_vigencia': meses_rce,
            'fecha_inicio_requerida': fecha_inicio_rce,
            'fecha_fin_requerida': fecha_fin_rce,
            'detalles': detalles_rce,
            'otrosi_modificador': obtener_identificador_modificador(otrosi_modificador_rce)
        }
    
    # Póliza Cumplimiento
    exige_cumplimiento = obtener_bool('nuevo_exige_poliza_cumplimiento', 'exige_poliza_cumplimiento')
    if exige_cumplimiento:
        meses_cumplimiento = obtener_valor('nuevo_meses_vigencia_cumplimiento', 'meses_vigencia_cumplimiento')
        fecha_inicio_cumplimiento = obtener_valor('nuevo_fecha_inicio_vigencia_cumplimiento', 'fecha_inicio_vigencia_cumplimiento')
        fecha_fin_cumplimiento = obtener_valor('nuevo_fecha_fin_vigencia_cumplimiento', 'fecha_fin_vigencia_cumplimiento')
        
        if not fecha_fin_cumplimiento and fecha_inicio_cumplimiento and meses_cumplimiento:
            from .utils import calcular_fecha_vencimiento
            fecha_fin_cumplimiento = calcular_fecha_vencimiento(fecha_inicio_cumplimiento, meses_cumplimiento)
        elif not fecha_inicio_cumplimiento and meses_cumplimiento and contrato.fecha_final_actualizada:
            from .utils import calcular_fecha_vencimiento
            fecha_fin_cumplimiento = calcular_fecha_vencimiento(contrato.fecha_final_actualizada, meses_cumplimiento)
        
        detalles_cumplimiento = {
            'remuneraciones': obtener_valor('nuevo_valor_remuneraciones_cumplimiento', 'valor_remuneraciones_cumplimiento'),
            'servicios_publicos': obtener_valor('nuevo_valor_servicios_publicos_cumplimiento', 'valor_servicios_publicos_cumplimiento'),
            'iva': obtener_valor('nuevo_valor_iva_cumplimiento', 'valor_iva_cumplimiento'),
            'cuota_admon': obtener_valor('nuevo_valor_otros_cumplimiento', 'valor_otros_cumplimiento'),
        }
        
        # Si es PROVEEDOR, agregar amparos de Cumplimiento específicos
        if contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR':
            detalles_cumplimiento.update({
                'cumplimiento_contrato': obtener_valor('nuevo_cumplimiento_amparo_cumplimiento_contrato', 'cumplimiento_amparo_cumplimiento_contrato'),
                'buen_manejo_anticipo': obtener_valor('nuevo_cumplimiento_amparo_buen_manejo_anticipo', 'cumplimiento_amparo_buen_manejo_anticipo'),
                'amortizacion_anticipo': obtener_valor('nuevo_cumplimiento_amparo_amortizacion_anticipo', 'cumplimiento_amparo_amortizacion_anticipo'),
                'salarios_prestaciones': obtener_valor('nuevo_cumplimiento_amparo_salarios_prestaciones', 'cumplimiento_amparo_salarios_prestaciones'),
                'aportes_seguridad_social': obtener_valor('nuevo_cumplimiento_amparo_aportes_seguridad_social', 'cumplimiento_amparo_aportes_seguridad_social'),
                'calidad_servicio': obtener_valor('nuevo_cumplimiento_amparo_calidad_servicio', 'cumplimiento_amparo_calidad_servicio'),
                'estabilidad_obra': obtener_valor('nuevo_cumplimiento_amparo_estabilidad_obra', 'cumplimiento_amparo_estabilidad_obra'),
                'calidad_bienes': obtener_valor('nuevo_cumplimiento_amparo_calidad_bienes', 'cumplimiento_amparo_calidad_bienes'),
                'multas': obtener_valor('nuevo_cumplimiento_amparo_multas', 'cumplimiento_amparo_multas'),
                'clausula_penal': obtener_valor('nuevo_cumplimiento_amparo_clausula_penal', 'cumplimiento_amparo_clausula_penal'),
                'sanciones_incumplimiento': obtener_valor('nuevo_cumplimiento_amparo_sanciones_incumplimiento', 'cumplimiento_amparo_sanciones_incumplimiento'),
            })
        
        # Obtener el Otro Sí que modificó el valor principal para determinar la fuente
        valor_cumplimiento, otrosi_valor_cumplimiento = obtener_valor_y_otrosi('nuevo_valor_asegurado_cumplimiento', 'valor_asegurado_cumplimiento')
        otrosi_modificador_cumplimiento = otrosi_valor_cumplimiento
        
        polizas_requeridas['Cumplimiento'] = {
            'tipo': 'Cumplimiento',
            'valor_requerido': valor_cumplimiento,
            'meses_vigencia': meses_cumplimiento,
            'fecha_inicio_requerida': fecha_inicio_cumplimiento,
            'fecha_fin_requerida': fecha_fin_cumplimiento,
            'detalles': detalles_cumplimiento,
            'otrosi_modificador': obtener_identificador_modificador(otrosi_modificador_cumplimiento)
        }
    
    # Póliza de Arrendamiento
    exige_arrendamiento = obtener_bool('nuevo_exige_poliza_arrendamiento', 'exige_poliza_arrendamiento')
    if exige_arrendamiento:
        meses_arrendamiento = obtener_valor('nuevo_meses_vigencia_arrendamiento', 'meses_vigencia_arrendamiento')
        fecha_inicio_arrendamiento = obtener_valor('nuevo_fecha_inicio_vigencia_arrendamiento', 'fecha_inicio_vigencia_arrendamiento')
        fecha_fin_arrendamiento = obtener_valor('nuevo_fecha_fin_vigencia_arrendamiento', 'fecha_fin_vigencia_arrendamiento')
        
        if not fecha_fin_arrendamiento and fecha_inicio_arrendamiento and meses_arrendamiento:
            from .utils import calcular_fecha_vencimiento
            fecha_fin_arrendamiento = calcular_fecha_vencimiento(fecha_inicio_arrendamiento, meses_arrendamiento)
        elif not fecha_inicio_arrendamiento and meses_arrendamiento and contrato.fecha_final_actualizada:
            from .utils import calcular_fecha_vencimiento
            fecha_fin_arrendamiento = calcular_fecha_vencimiento(contrato.fecha_final_actualizada, meses_arrendamiento)
        
        # Obtener el Otro Sí que modificó el valor principal para determinar la fuente
        valor_arrendamiento, otrosi_valor_arrendamiento = obtener_valor_y_otrosi('nuevo_valor_asegurado_arrendamiento', 'valor_asegurado_arrendamiento')
        otrosi_modificador_arrendamiento = otrosi_valor_arrendamiento
        
        polizas_requeridas['Poliza de Arrendamiento'] = {
            'tipo': 'Poliza de Arrendamiento',
            'valor_requerido': valor_arrendamiento,
            'meses_vigencia': meses_arrendamiento,
            'fecha_inicio_requerida': fecha_inicio_arrendamiento,
            'fecha_fin_requerida': fecha_fin_arrendamiento,
            'detalles': {
                'remuneraciones': obtener_valor('nuevo_valor_remuneraciones_arrendamiento', 'valor_remuneraciones_arrendamiento'),
                'servicios_publicos': obtener_valor('nuevo_valor_servicios_publicos_arrendamiento', 'valor_servicios_publicos_arrendamiento'),
                'iva': obtener_valor('nuevo_valor_iva_arrendamiento', 'valor_iva_arrendamiento'),
                'cuota_admon': obtener_valor('nuevo_valor_otros_arrendamiento', 'valor_otros_arrendamiento'),
            },
            'otrosi_modificador': obtener_identificador_modificador(otrosi_modificador_arrendamiento)
        }
    
    # Póliza Todo Riesgo
    exige_todo_riesgo = obtener_bool('nuevo_exige_poliza_todo_riesgo', 'exige_poliza_todo_riesgo')
    if exige_todo_riesgo:
        meses_todo_riesgo = obtener_valor('nuevo_meses_vigencia_todo_riesgo', 'meses_vigencia_todo_riesgo')
        fecha_inicio_todo_riesgo = obtener_valor('nuevo_fecha_inicio_vigencia_todo_riesgo', 'fecha_inicio_vigencia_todo_riesgo')
        fecha_fin_todo_riesgo = obtener_valor('nuevo_fecha_fin_vigencia_todo_riesgo', 'fecha_fin_vigencia_todo_riesgo')
        
        if not fecha_fin_todo_riesgo and fecha_inicio_todo_riesgo and meses_todo_riesgo:
            from .utils import calcular_fecha_vencimiento
            fecha_fin_todo_riesgo = calcular_fecha_vencimiento(fecha_inicio_todo_riesgo, meses_todo_riesgo)
        elif not fecha_inicio_todo_riesgo and meses_todo_riesgo and contrato.fecha_final_actualizada:
            from .utils import calcular_fecha_vencimiento
            fecha_fin_todo_riesgo = calcular_fecha_vencimiento(contrato.fecha_final_actualizada, meses_todo_riesgo)
        
        # Obtener el Otro Sí que modificó el valor principal para determinar la fuente
        valor_todo_riesgo, otrosi_valor_todo_riesgo = obtener_valor_y_otrosi('nuevo_valor_asegurado_todo_riesgo', 'valor_asegurado_todo_riesgo')
        otrosi_modificador_todo_riesgo = otrosi_valor_todo_riesgo
        
        polizas_requeridas['Arrendamiento'] = {
            'tipo': 'Arrendamiento',
            'valor_requerido': valor_todo_riesgo,
            'meses_vigencia': meses_todo_riesgo,
            'fecha_inicio_requerida': fecha_inicio_todo_riesgo,
            'fecha_fin_requerida': fecha_fin_todo_riesgo,
            'otrosi_modificador': obtener_identificador_modificador(otrosi_modificador_todo_riesgo)
        }
    
    # Otras Pólizas
    exige_otra = obtener_bool('nuevo_exige_poliza_otra_1', 'exige_poliza_otra_1')
    if exige_otra:
        meses_otra = obtener_valor('nuevo_meses_vigencia_otra_1', 'meses_vigencia_otra_1')
        fecha_inicio_otra = obtener_valor('nuevo_fecha_inicio_vigencia_otra_1', 'fecha_inicio_vigencia_otra_1')
        fecha_fin_otra = obtener_valor('nuevo_fecha_fin_vigencia_otra_1', 'fecha_fin_vigencia_otra_1')
        
        if not fecha_fin_otra and fecha_inicio_otra and meses_otra:
            from .utils import calcular_fecha_vencimiento
            fecha_fin_otra = calcular_fecha_vencimiento(fecha_inicio_otra, meses_otra)
        elif not fecha_inicio_otra and meses_otra and contrato.fecha_final_actualizada:
            from .utils import calcular_fecha_vencimiento
            fecha_fin_otra = calcular_fecha_vencimiento(contrato.fecha_final_actualizada, meses_otra)
        
        nombre_otra = obtener_valor('nuevo_nombre_poliza_otra_1', 'nombre_poliza_otra_1') or 'Otra'
        # Obtener el Otro Sí que modificó el valor principal para determinar la fuente
        valor_otra, otrosi_valor_otra = obtener_valor_y_otrosi('nuevo_valor_asegurado_otra_1', 'valor_asegurado_otra_1')
        otrosi_modificador_otra = otrosi_valor_otra
        
        polizas_requeridas['Otra'] = {
            'tipo': 'Otra',
            'nombre': nombre_otra,
            'valor_requerido': valor_otra,
            'meses_vigencia': meses_otra,
            'fecha_inicio_requerida': fecha_inicio_otra,
            'fecha_fin_requerida': fecha_fin_otra,
            'otrosi_modificador': obtener_identificador_modificador(otrosi_modificador_otra)
        }
    
    return polizas_requeridas


def get_condiciones_polizas_vigentes(contrato, fecha_referencia=None):
    """
    Obtiene las condiciones de pólizas vigentes para un contrato.
    
    Usa get_polizas_requeridas_contrato que ya maneja los valores del OtroSi vigente
    cuando modifica_polizas=True.
    
    Retorna un diccionario con las condiciones de pólizas para mostrar en el formulario de Otro Sí.
    """
    if fecha_referencia is None:
        fecha_referencia = date.today()

    if es_fecha_fuera_vigencia_contrato(contrato, fecha_referencia):
        return {
            'fuente': 'contrato_fuera_vigencia',
            'otrosi_vigente': None,
            'polizas': {},
        }
    
    # Buscar el último Otro Sí vigente por fecha de aprobación
    otrosi_vigente = get_otrosi_vigente(contrato, fecha_referencia)
    
    # Obtener pólizas requeridas (ya considera OtroSi vigente si modifica_polizas=True)
    polizas_requeridas = get_polizas_requeridas_contrato(contrato, fecha_referencia)
    
    condiciones = {
        'fuente': 'otrosi_vigente' if (otrosi_vigente and otrosi_vigente.modifica_polizas) else 'contrato_base',
        'otrosi_vigente': otrosi_vigente,
        'polizas': polizas_requeridas
    }
    
    return condiciones


def validar_solapamiento_vigencias(contrato, effective_from, effective_to=None, excluir_otrosi_id=None):
    """
    Valida que no haya solapamiento de vigencias entre Otrosí del mismo contrato.
    
    Retorna (es_valido, mensaje_error)
    """
    from .models import OtroSi
    
    # Construir query
    query = Q(contrato=contrato, estado='APROBADO')
    
    if excluir_otrosi_id:
        query &= ~Q(id=excluir_otrosi_id)
    
    # Buscar solapamientos
    otrosis_existentes = OtroSi.objects.filter(query)
    
    for otrosi in otrosis_existentes:
        # Rangos del Otrosí existente
        inicio_existente = otrosi.effective_from
        fin_existente = otrosi.effective_to  # Puede ser None
        
        # Rangos del nuevo
        inicio_nuevo = effective_from
        fin_nuevo = effective_to  # Puede ser None
        
        # Verificar solapamiento
        # Caso 1: El nuevo comienza dentro del rango existente
        if fin_existente is None:
            # El existente no tiene fin, entonces cualquier fecha >= inicio_existente solapa
            if inicio_nuevo >= inicio_existente:
                return False, f"Solapa con {_obtener_label_evento(otrosi)} que inicia en {inicio_existente} sin fecha fin"
        else:
            if inicio_existente <= inicio_nuevo <= fin_existente:
                return False, f"La fecha de inicio solapa con {_obtener_label_evento(otrosi)} ({inicio_existente} - {fin_existente})"
        
        # Caso 2: El nuevo termina dentro del rango existente
        if fin_nuevo:
            if fin_existente is None:
                if fin_nuevo >= inicio_existente:
                    return False, f"La fecha de fin solapa con {_obtener_label_evento(otrosi)} que inicia en {inicio_existente}"
            else:
                if inicio_existente <= fin_nuevo <= fin_existente:
                    return False, f"La fecha de fin solapa con {_obtener_label_evento(otrosi)} ({inicio_existente} - {fin_existente})"
        
        # Caso 3: El nuevo envuelve completamente al existente
        if fin_existente:
            if fin_nuevo is None:
                if inicio_nuevo <= inicio_existente:
                    return False, f"El rango envuelve a {_obtener_label_evento(otrosi)}"
            else:
                if inicio_nuevo <= inicio_existente and fin_nuevo >= fin_existente:
                    return False, f"El rango envuelve a {_obtener_label_evento(otrosi)}"
    
    return True, None


def obtener_valores_vigentes_facturacion_ventas(contrato, mes, año):
    """
    Obtiene los valores vigentes necesarios para el cálculo de facturación por ventas
    para un mes y año específicos.
    
    Args:
        contrato: Instancia del modelo Contrato
        mes: Mes (1-12)
        año: Año
    
    Returns:
        dict con:
        - modalidad: Modalidad vigente ('Variable Puro' o 'Híbrido (Min Garantizado)')
        - porcentaje_ventas: Porcentaje de ventas vigente
        - canon_minimo_garantizado: Canon mínimo garantizado vigente (si aplica)
        - canon_fijo: Canon fijo vigente (si aplica)
        - otrosi_referencia: Otro Sí vigente usado para el cálculo
    """
    # Crear fecha de referencia (último día del mes)
    from calendar import monthrange
    ultimo_dia = monthrange(año, mes)[1]
    fecha_referencia = date(año, mes, ultimo_dia)
    
    otrosi_referencia = None

    if es_fecha_fuera_vigencia_contrato(contrato, fecha_referencia):
        return None
    
    # Obtener modalidad vigente usando efecto cadena
    otrosi_modalidad = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato, 'nueva_modalidad_pago', fecha_referencia
    )
    if otrosi_modalidad and otrosi_modalidad.nueva_modalidad_pago:
        modalidad = otrosi_modalidad.nueva_modalidad_pago
        otrosi_referencia = otrosi_modalidad
    else:
        modalidad = contrato.modalidad_pago
    
    if modalidad not in ['Variable Puro', 'Hibrido (Min Garantizado)']:
        return None
    
    # Obtener porcentaje vigente
    otrosi_porcentaje = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato, 'nuevo_porcentaje_ventas', fecha_referencia
    )
    if otrosi_porcentaje and otrosi_porcentaje.nuevo_porcentaje_ventas is not None:
        porcentaje_ventas = Decimal(str(otrosi_porcentaje.nuevo_porcentaje_ventas))
        # Solo establecer otrosi_referencia si el valor es diferente del contrato base
        porcentaje_contrato_base = contrato.porcentaje_ventas
        if porcentaje_contrato_base is None or Decimal(str(porcentaje_ventas)) != Decimal(str(porcentaje_contrato_base)):
            otrosi_referencia = otrosi_referencia or otrosi_porcentaje
    elif contrato.porcentaje_ventas is not None:
        porcentaje_ventas = Decimal(str(contrato.porcentaje_ventas))
    else:
        return None
    
    canon_minimo_garantizado = None
    if modalidad == 'Hibrido (Min Garantizado)':
        otrosi_canon_min = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nuevo_canon_minimo_garantizado', fecha_referencia
        )
        if otrosi_canon_min and otrosi_canon_min.nuevo_canon_minimo_garantizado is not None:
            canon_minimo_garantizado = Decimal(str(otrosi_canon_min.nuevo_canon_minimo_garantizado))
            otrosi_referencia = otrosi_referencia or otrosi_canon_min
        elif contrato.canon_minimo_garantizado is not None:
            canon_minimo_garantizado = Decimal(str(contrato.canon_minimo_garantizado))
    
    otrosi_canon_fijo = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato, 'nuevo_valor_canon', fecha_referencia
    )
    if otrosi_canon_fijo and otrosi_canon_fijo.nuevo_valor_canon is not None:
        canon_fijo = Decimal(str(otrosi_canon_fijo.nuevo_valor_canon))
        otrosi_referencia = otrosi_referencia or otrosi_canon_fijo
    elif contrato.valor_canon_fijo is not None:
        canon_fijo = Decimal(str(contrato.valor_canon_fijo))
    else:
        canon_fijo = None
    
    # No establecer otrosi_referencia como fallback si ningún campo fue modificado
    # Solo debe mostrarse si realmente se modificó algún campo relevante
    
    # Determinar referencias específicas por campo
    otrosi_referencia_porcentaje = None
    otrosi_referencia_canon_minimo = None
    
    # Referencia para porcentaje de ventas
    if otrosi_porcentaje and otrosi_porcentaje.nuevo_porcentaje_ventas is not None:
        porcentaje_contrato_base = contrato.porcentaje_ventas
        if porcentaje_contrato_base is None or Decimal(str(otrosi_porcentaje.nuevo_porcentaje_ventas)) != Decimal(str(porcentaje_contrato_base)):
            otrosi_referencia_porcentaje = otrosi_porcentaje
    
    # Referencia para canon mínimo
    if modalidad == 'Hibrido (Min Garantizado)':
        if otrosi_canon_min and otrosi_canon_min.nuevo_canon_minimo_garantizado is not None:
            canon_min_contrato_base = contrato.canon_minimo_garantizado
            if canon_min_contrato_base is None or Decimal(str(otrosi_canon_min.nuevo_canon_minimo_garantizado)) != Decimal(str(canon_min_contrato_base)):
                otrosi_referencia_canon_minimo = otrosi_canon_min
    
    return {
        'modalidad': modalidad,
        'porcentaje_ventas': porcentaje_ventas,
        'canon_minimo_garantizado': canon_minimo_garantizado,
        'canon_fijo': canon_fijo,
        'otrosi_referencia': otrosi_referencia,  # Mantener para compatibilidad
        'otrosi_referencia_porcentaje': otrosi_referencia_porcentaje,
        'otrosi_referencia_canon_minimo': otrosi_referencia_canon_minimo,
        'fecha_referencia': fecha_referencia,
    }


def procesar_renovacion_automatica(contrato, usuario, meses_renovacion=None, usar_duracion_inicial=True, datos_polizas=None):
    """
    Procesa la renovación automática de un contrato creando un evento de renovación automática.
    Actualiza directamente la fecha final del contrato sin crear OtroSi.
    Si se proporcionan datos de pólizas y modifica_polizas=True, actualiza las condiciones de pólizas del contrato.
    
    Args:
        contrato: Instancia del modelo Contrato con prorroga_automatica=True
        usuario: Usuario que autoriza la renovación
        meses_renovacion: Número de meses para la renovación (opcional, si no se usa duracion_inicial)
        usar_duracion_inicial: Si True, usa la duración inicial del contrato. Si False, usa meses_renovacion.
        datos_polizas: Diccionario con los datos de pólizas del formulario (opcional)
    
    Returns:
        RenovacionAutomatica creada o None si hay error
    """
    from .models import RenovacionAutomatica
    from gestion.utils import calcular_fecha_vencimiento
    from django.utils import timezone
    from datetime import timedelta
    
    if not contrato.prorroga_automatica:
        return None
    
    fecha_actual = date.today()
    evento_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato, 'nueva_fecha_final_actualizada', fecha_actual
    )
    
    if evento_modificador:
        # Puede ser OtroSi o RenovacionAutomatica
        if hasattr(evento_modificador, 'nueva_fecha_final_actualizada'):
            fecha_fin_actual = evento_modificador.nueva_fecha_final_actualizada
        else:
            fecha_fin_actual = contrato.fecha_final_actualizada or contrato.fecha_final_inicial
    else:
        fecha_fin_actual = contrato.fecha_final_actualizada or contrato.fecha_final_inicial
    
    if not fecha_fin_actual:
        return None
    
    fecha_final_anterior = fecha_fin_actual
    
    if usar_duracion_inicial:
        meses_renovacion = contrato.duracion_inicial_meses
    elif not meses_renovacion:
        return None
    
    nueva_fecha_final = calcular_fecha_vencimiento(fecha_fin_actual, meses_renovacion)
    fecha_inicio_renovacion = fecha_fin_actual + timedelta(days=1)
    
    username = usuario.get_username() if hasattr(usuario, "get_username") else str(usuario)
    
    modifica_polizas = datos_polizas and datos_polizas.get('modifica_polizas', False)
    
    renovacion = RenovacionAutomatica(
        contrato=contrato,
        fecha_renovacion=fecha_actual,
        effective_from=fecha_inicio_renovacion,
        fecha_inicio_nueva_vigencia=fecha_inicio_renovacion,
        nueva_fecha_final_actualizada=nueva_fecha_final,
        meses_renovacion=meses_renovacion,
        usar_duracion_inicial=usar_duracion_inicial,
        fecha_final_anterior=fecha_final_anterior,
        estado='APROBADO',
        creado_por=username,
        aprobado_por=username,
        fecha_aprobacion=timezone.now(),
        descripcion=f'Renovación automática por {meses_renovacion} meses. Autorizada por {username}.',
        observaciones=f'Renovación automática por {meses_renovacion} meses. Autorizada por {username}.',
        modifica_polizas=modifica_polizas,
    )
    
    if datos_polizas and modifica_polizas:
        campos_polizas = [
            'nuevo_exige_poliza_rce', 'nuevo_valor_asegurado_rce', 'nuevo_valor_propietario_locatario_ocupante_rce',
            'nuevo_valor_patronal_rce', 'nuevo_valor_gastos_medicos_rce', 'nuevo_valor_vehiculos_rce',
            'nuevo_valor_contratistas_rce', 'nuevo_valor_perjuicios_extrapatrimoniales_rce',
            'nuevo_valor_dano_moral_rce', 'nuevo_valor_lucro_cesante_rce', 'nuevo_meses_vigencia_rce',
            'nuevo_fecha_inicio_vigencia_rce', 'nuevo_fecha_fin_vigencia_rce',
            'nuevo_exige_poliza_cumplimiento', 'nuevo_valor_asegurado_cumplimiento',
            'nuevo_valor_remuneraciones_cumplimiento', 'nuevo_valor_servicios_publicos_cumplimiento',
            'nuevo_valor_iva_cumplimiento', 'nuevo_valor_otros_cumplimiento',
            'nuevo_meses_vigencia_cumplimiento', 'nuevo_fecha_inicio_vigencia_cumplimiento',
            'nuevo_fecha_fin_vigencia_cumplimiento',
            'nuevo_exige_poliza_arrendamiento', 'nuevo_valor_asegurado_arrendamiento',
            'nuevo_valor_remuneraciones_arrendamiento', 'nuevo_valor_servicios_publicos_arrendamiento',
            'nuevo_valor_iva_arrendamiento', 'nuevo_valor_otros_arrendamiento',
            'nuevo_meses_vigencia_arrendamiento', 'nuevo_fecha_inicio_vigencia_arrendamiento',
            'nuevo_fecha_fin_vigencia_arrendamiento',
            'nuevo_exige_poliza_todo_riesgo', 'nuevo_valor_asegurado_todo_riesgo',
            'nuevo_meses_vigencia_todo_riesgo', 'nuevo_fecha_inicio_vigencia_todo_riesgo',
            'nuevo_fecha_fin_vigencia_todo_riesgo',
            'nuevo_exige_poliza_otra_1', 'nuevo_nombre_poliza_otra_1', 'nuevo_valor_asegurado_otra_1',
            'nuevo_meses_vigencia_otra_1', 'nuevo_fecha_inicio_vigencia_otra_1',
            'nuevo_fecha_fin_vigencia_otra_1',
        ]
        
        for campo in campos_polizas:
            valor = datos_polizas.get(campo)
            if valor is not None:
                setattr(renovacion, campo, valor)
    
    renovacion.save()
    
    contrato.fecha_final_actualizada = nueva_fecha_final
    contrato.ultima_renovacion_automatica_por = username
    contrato.fecha_ultima_renovacion_automatica = timezone.now().date()
    contrato.total_renovaciones_automaticas += 1
    
    if modifica_polizas and datos_polizas:
        campos_contrato_polizas = {
            'exige_poliza_rce': datos_polizas.get('nuevo_exige_poliza_rce'),
            'valor_asegurado_rce': datos_polizas.get('nuevo_valor_asegurado_rce'),
            'valor_propietario_locatario_ocupante_rce': datos_polizas.get('nuevo_valor_propietario_locatario_ocupante_rce'),
            'valor_patronal_rce': datos_polizas.get('nuevo_valor_patronal_rce'),
            'valor_gastos_medicos_rce': datos_polizas.get('nuevo_valor_gastos_medicos_rce'),
            'valor_vehiculos_rce': datos_polizas.get('nuevo_valor_vehiculos_rce'),
            'valor_contratistas_rce': datos_polizas.get('nuevo_valor_contratistas_rce'),
            'valor_perjuicios_extrapatrimoniales_rce': datos_polizas.get('nuevo_valor_perjuicios_extrapatrimoniales_rce'),
            'valor_dano_moral_rce': datos_polizas.get('nuevo_valor_dano_moral_rce'),
            'valor_lucro_cesante_rce': datos_polizas.get('nuevo_valor_lucro_cesante_rce'),
            'meses_vigencia_rce': datos_polizas.get('nuevo_meses_vigencia_rce'),
            'fecha_inicio_vigencia_rce': datos_polizas.get('nuevo_fecha_inicio_vigencia_rce'),
            'fecha_fin_vigencia_rce': datos_polizas.get('nuevo_fecha_fin_vigencia_rce'),
            'exige_poliza_cumplimiento': datos_polizas.get('nuevo_exige_poliza_cumplimiento'),
            'valor_asegurado_cumplimiento': datos_polizas.get('nuevo_valor_asegurado_cumplimiento'),
            'valor_remuneraciones_cumplimiento': datos_polizas.get('nuevo_valor_remuneraciones_cumplimiento'),
            'valor_servicios_publicos_cumplimiento': datos_polizas.get('nuevo_valor_servicios_publicos_cumplimiento'),
            'valor_iva_cumplimiento': datos_polizas.get('nuevo_valor_iva_cumplimiento'),
            'valor_otros_cumplimiento': datos_polizas.get('nuevo_valor_otros_cumplimiento'),
            'meses_vigencia_cumplimiento': datos_polizas.get('nuevo_meses_vigencia_cumplimiento'),
            'fecha_inicio_vigencia_cumplimiento': datos_polizas.get('nuevo_fecha_inicio_vigencia_cumplimiento'),
            'fecha_fin_vigencia_cumplimiento': datos_polizas.get('nuevo_fecha_fin_vigencia_cumplimiento'),
            'exige_poliza_arrendamiento': datos_polizas.get('nuevo_exige_poliza_arrendamiento'),
            'valor_asegurado_arrendamiento': datos_polizas.get('nuevo_valor_asegurado_arrendamiento'),
            'valor_remuneraciones_arrendamiento': datos_polizas.get('nuevo_valor_remuneraciones_arrendamiento'),
            'valor_servicios_publicos_arrendamiento': datos_polizas.get('nuevo_valor_servicios_publicos_arrendamiento'),
            'valor_iva_arrendamiento': datos_polizas.get('nuevo_valor_iva_arrendamiento'),
            'valor_otros_arrendamiento': datos_polizas.get('nuevo_valor_otros_arrendamiento'),
            'meses_vigencia_arrendamiento': datos_polizas.get('nuevo_meses_vigencia_arrendamiento'),
            'fecha_inicio_vigencia_arrendamiento': datos_polizas.get('nuevo_fecha_inicio_vigencia_arrendamiento'),
            'fecha_fin_vigencia_arrendamiento': datos_polizas.get('nuevo_fecha_fin_vigencia_arrendamiento'),
            'exige_poliza_todo_riesgo': datos_polizas.get('nuevo_exige_poliza_todo_riesgo'),
            'valor_asegurado_todo_riesgo': datos_polizas.get('nuevo_valor_asegurado_todo_riesgo'),
            'meses_vigencia_todo_riesgo': datos_polizas.get('nuevo_meses_vigencia_todo_riesgo'),
            'fecha_inicio_vigencia_todo_riesgo': datos_polizas.get('nuevo_fecha_inicio_vigencia_todo_riesgo'),
            'fecha_fin_vigencia_todo_riesgo': datos_polizas.get('nuevo_fecha_fin_vigencia_todo_riesgo'),
            'exige_poliza_otra_1': datos_polizas.get('nuevo_exige_poliza_otra_1'),
            'nombre_poliza_otra_1': datos_polizas.get('nuevo_nombre_poliza_otra_1'),
            'valor_asegurado_otra_1': datos_polizas.get('nuevo_valor_asegurado_otra_1'),
            'meses_vigencia_otra_1': datos_polizas.get('nuevo_meses_vigencia_otra_1'),
            'fecha_inicio_vigencia_otra_1': datos_polizas.get('nuevo_fecha_inicio_vigencia_otra_1'),
            'fecha_fin_vigencia_otra_1': datos_polizas.get('nuevo_fecha_fin_vigencia_otra_1'),
        }
        
        for campo_contrato, valor in campos_contrato_polizas.items():
            if valor is not None:
                setattr(contrato, campo_contrato, valor)
    
    contrato.save()
    
    return renovacion

