"""
Utilidades para gestión de Otrosí y vistas vigentes de contratos
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db.models import Q


def _obtener_numero_evento(evento):
    """Retorna el número del evento (Otro Sí o Renovación Automática)."""
    try:
        if not evento:
            return None
        if hasattr(evento, 'numero_otrosi'):
            return getattr(evento, 'numero_otrosi', None)
        if hasattr(evento, 'numero_renovacion'):
            return getattr(evento, 'numero_renovacion', None)
        return str(evento)
    except Exception:
        return None


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
    Determina si una fecha está fuera de la vigencia del contrato.
    Retorna True si la fecha es anterior al inicio o posterior a la fecha final del contrato.
    """
    try:
        if not fecha_referencia:
            return False
        
        fecha_inicio = getattr(contrato, 'fecha_inicial_contrato', None)
        if fecha_inicio and fecha_referencia < fecha_inicio:
            return True
        
        try:
            from gestion.views.utils import _obtener_fecha_final_contrato
            fecha_final = _obtener_fecha_final_contrato(contrato, fecha_referencia)
            if fecha_final and fecha_referencia > fecha_final:
                return True
        except Exception:
            # Si hay error al obtener fecha final, usar fecha_final_inicial como fallback
            fecha_final = getattr(contrato, 'fecha_final_inicial', None)
            if fecha_final and fecha_referencia > fecha_final:
                return True
        
        return False
    except Exception:
        # Si hay cualquier error, retornar False para evitar bloquear la aplicación
        return False


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
            # Para Decimal, verificar que no sea 0 (0 puede indicar que no se modificó)
            elif isinstance(valor, (Decimal, int, float)):
                # Convertir a Decimal para comparación
                try:
                    valor_decimal = Decimal(str(valor)) if valor is not None else None
                    # Para campos financieros, 0 generalmente significa que no se modificó
                    # Solo retornar si el valor es diferente de 0
                    if valor_decimal is not None and valor_decimal != Decimal('0'):
                        return evento
                except (ValueError, TypeError):
                    # Si no se puede convertir a Decimal, tratar como valor válido
                    return evento
            # Para otros tipos (bool, date), si no es None, es válido
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
        fecha_inicio = getattr(contrato, 'fecha_inicial_contrato', None)
        from gestion.views.utils import _obtener_fecha_final_contrato
        fecha_final = _obtener_fecha_final_contrato(contrato, fecha_referencia)
        
        mensaje = None
        if fecha_inicio and fecha_referencia < fecha_inicio:
            mensaje = (
                f'La fecha {fecha_referencia} es anterior al inicio del contrato '
                f'({fecha_inicio}).'
            )
        elif fecha_final and fecha_referencia > fecha_final:
            mensaje = (
                f'La fecha {fecha_referencia} está fuera de la vigencia del contrato. '
                f'El contrato está vigente hasta {fecha_final}. '
                f'Según la documentación (Contrato, Otro Sí o Renovación Automática), '
                f'solo estos tres tipos de documentos pueden aumentar la vigencia del contrato. '
                f'Para la fecha seleccionada, el contrato no está activo.'
            )
        else:
            mensaje = f'La fecha {fecha_referencia} está fuera de la vigencia del contrato.'
        
        return {
            'contrato': contrato,
            'num_contrato': getattr(contrato, 'num_contrato', ''),
            'fecha_referencia': fecha_referencia,
            'otrosi_vigente': None,
            'campos_modificados': {},
            'tiene_modificaciones': False,
            'vista_disponible': False,
            'mensaje_sin_vigencia': mensaje,
        }
    
    def obtener_valor_vigente_antes_de_otrosi(otrosi_modificador, campo_contrato):
        """
        Obtiene el valor vigente del contrato ANTES de que se aplicara el Otro Sí.
        Esto permite verificar si el Otro Sí realmente modificó el campo o solo mantuvo el valor existente.
        
        Args:
            otrosi_modificador: Instancia del OtroSi a verificar
            campo_contrato: Nombre del campo en Contrato (ej: 'valor_canon_fijo')
        
        Returns:
            Valor vigente antes del Otro Sí o None
        """
        try:
            # Validaciones básicas
            if not otrosi_modificador:
                return getattr(contrato, campo_contrato, None)
            
            if not hasattr(otrosi_modificador, 'effective_from'):
                return getattr(contrato, campo_contrato, None)
            
            if not otrosi_modificador.effective_from:
                return getattr(contrato, campo_contrato, None)
            
            # Obtener la fecha anterior al effective_from del Otro Sí
            effective_from_value = otrosi_modificador.effective_from
            
            # Convertir a date si es datetime
            if isinstance(effective_from_value, datetime):
                effective_from_value = effective_from_value.date()
            elif not isinstance(effective_from_value, date):
                # Si no es date ni datetime, retornar valor del contrato base
                return getattr(contrato, campo_contrato, None)
            
            fecha_anterior = effective_from_value - timedelta(days=1)
            
            # Validar que la fecha anterior sea válida
            if fecha_anterior < date(1900, 1, 1):
                return getattr(contrato, campo_contrato, None)
            
            # Mapear el campo del contrato al campo en OtroSi
            mapeo_campos_otrosi = {
                'valor_canon_fijo': 'nuevo_valor_canon',
                'modalidad_pago': 'nueva_modalidad_pago',
                'canon_minimo_garantizado': 'nuevo_canon_minimo_garantizado',
                'porcentaje_ventas': 'nuevo_porcentaje_ventas',
            }
            
            campo_otrosi = mapeo_campos_otrosi.get(campo_contrato)
            
            # Si no hay mapeo, retornar valor del contrato base
            if not campo_otrosi:
                return getattr(contrato, campo_contrato, None)
            
            # Buscar el último Otro Sí que modificó este campo antes de la fecha del Otro Sí actual
            try:
                otrosi_anterior = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
                    contrato, campo_otrosi, fecha_anterior
                )
                
                if otrosi_anterior and otrosi_anterior.id != otrosi_modificador.id:
                    valor_anterior = getattr(otrosi_anterior, campo_otrosi, None)
                    if valor_anterior is not None:
                        # Para strings, verificar que no esté vacío
                        if isinstance(valor_anterior, str):
                            if valor_anterior.strip() != '':
                                return valor_anterior
                        # Para Decimal y otros tipos numéricos, verificar que no sea 0
                        else:
                            from decimal import Decimal
                            try:
                                if isinstance(valor_anterior, Decimal):
                                    if valor_anterior != Decimal('0'):
                                        return valor_anterior
                                else:
                                    # Intentar convertir a Decimal
                                    valor_decimal = Decimal(str(valor_anterior))
                                    if valor_decimal != Decimal('0'):
                                        return valor_anterior
                            except (ValueError, TypeError):
                                # Si no se puede convertir, retornar el valor tal cual
                                return valor_anterior
            except Exception:
                # Si hay error al buscar Otro Sí anterior, usar valor del contrato base
                pass
            
            # Si no hay Otro Sí anterior que lo modificó, usar valor del contrato base
            return getattr(contrato, campo_contrato, None)
        except Exception:
            # Si hay algún error, retornar el valor del contrato base
            return getattr(contrato, campo_contrato, None)
    
    # Función auxiliar para obtener valor de un campo con efecto cadena
    def obtener_valor_campo(campo_otrosi, campo_contrato, tipo='valor'):
        """
        Obtiene el valor de un campo usando efecto cadena.
        
        Si encuentra un Otro Sí que modificó el campo, retorna ese valor.
        Si no encuentra un Otro Sí o el Otro Sí no tiene un valor válido, retorna el valor del contrato base.
        
        Args:
            campo_otrosi: Nombre del campo en OtroSi (ej: 'nuevo_valor_canon')
            campo_contrato: Nombre del campo en Contrato (ej: 'valor_canon_fijo')
            tipo: 'valor', 'bool', 'fecha'
        """
        # Obtener valor del contrato base primero
        valor_contrato = getattr(contrato, campo_contrato, None)
        
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, campo_otrosi, fecha_referencia
        )
        
        if otrosi_modificador:
            valor = getattr(otrosi_modificador, campo_otrosi, None)
            if valor is not None:
                # Para strings, verificar que no esté vacío
                if isinstance(valor, str) and valor.strip() != '':
                    return valor, otrosi_modificador
                # Para Decimal y otros tipos numéricos, verificar que no sea 0
                elif not isinstance(valor, str):
                    from decimal import Decimal
                    # Si es Decimal, verificar que no sea 0
                    if isinstance(valor, Decimal) and valor == Decimal('0'):
                        # Si el Otro Sí tiene 0, usar el valor del contrato base
                        return valor_contrato, None
                    # Para otros tipos numéricos o valores válidos, retornar el valor del Otro Sí
                    return valor, otrosi_modificador
        
        # Si no hay Otro Sí que lo modificó o el Otro Sí no tiene valor válido, usar valor del contrato
        return valor_contrato, None
    
    # Vista base del contrato
    try:
        otrosi_vigente = get_otrosi_vigente(contrato, fecha_referencia)
    except Exception:
        otrosi_vigente = None
    
    vista = {
        # Datos base
        'contrato': contrato,
        'num_contrato': getattr(contrato, 'num_contrato', ''),
        'fecha_referencia': fecha_referencia,
        
        # Metadata
        'otrosi_vigente': otrosi_vigente,
        'campos_modificados': {},
        'tiene_modificaciones': False,
        'vista_disponible': True,
        'mensaje_sin_vigencia': None,
    }
    
    # Obtener valores con efecto cadena para campos financieros
    # Solo marcar como modificado si el Otro Sí realmente tiene un valor en ese campo
    # Y ese valor es diferente del valor vigente antes del Otro Sí
    try:
        valor_canon, otrosi_canon = obtener_valor_campo('nuevo_valor_canon', 'valor_canon_fijo')
    except Exception:
        valor_canon = getattr(contrato, 'valor_canon_fijo', None)
        otrosi_canon = None
    
    vista['valor_canon'] = valor_canon
    # Verificar si el Otro Sí realmente modificó el campo:
    # 1. Debe tener un valor no nulo/no vacío en el campo
    # 2. Ese valor debe ser diferente del valor vigente ANTES del Otro Sí
    if otrosi_canon and valor_canon is not None:
        try:
            # Verificar que el campo realmente tenga un valor válido (no None, no 0 para Decimal)
            from decimal import Decimal
            valor_otrosi_decimal = Decimal(str(valor_canon)) if valor_canon else None
            if valor_otrosi_decimal is not None and valor_otrosi_decimal != Decimal('0'):
                # Obtener el valor que estaba vigente ANTES de este Otro Sí
                valor_antes_otrosi = obtener_valor_vigente_antes_de_otrosi(otrosi_canon, 'valor_canon_fijo')
                
                # Comparar valores considerando None y Decimal
                es_diferente = False
                if valor_antes_otrosi is None:
                    es_diferente = True  # Si no había valor antes y ahora sí hay, fue modificado
                elif valor_antes_otrosi is not None:
                    try:
                        # Convertir a Decimal para comparación precisa
                        canon_antes = Decimal(str(valor_antes_otrosi)) if valor_antes_otrosi else None
                        if canon_antes is not None and valor_otrosi_decimal is not None:
                            es_diferente = canon_antes != valor_otrosi_decimal
                    except (ValueError, TypeError):
                        # Si hay error al convertir, comparar directamente
                        es_diferente = valor_antes_otrosi != valor_canon
                
                if es_diferente:
                    vista['campos_modificados']['valor_canon'] = {
                        'original': valor_antes_otrosi,
                        'nuevo': valor_canon,
                        'otrosi': _obtener_numero_evento(otrosi_canon),
                        'version': getattr(otrosi_canon, 'version', 1)
                    }
                    vista['tiene_modificaciones'] = True
        except Exception:
            # Si hay algún error, continuar sin marcar como modificado
            pass
    
    try:
        modalidad_pago, otrosi_modalidad = obtener_valor_campo('nueva_modalidad_pago', 'modalidad_pago')
    except Exception:
        modalidad_pago = getattr(contrato, 'modalidad_pago', None)
        otrosi_modalidad = None
    
    vista['modalidad_pago'] = modalidad_pago
    # Verificar si el Otro Sí realmente modificó el campo comparando con el valor vigente ANTES del Otro Sí
    if otrosi_modalidad and modalidad_pago:
        try:
            # Obtener el valor que estaba vigente ANTES de este Otro Sí
            modalidad_antes_otrosi = obtener_valor_vigente_antes_de_otrosi(otrosi_modalidad, 'modalidad_pago')
            # Comparar valores de modalidad
            if modalidad_antes_otrosi != modalidad_pago:
                vista['campos_modificados']['modalidad_pago'] = {
                    'original': modalidad_antes_otrosi,
                    'nuevo': modalidad_pago,
                    'otrosi': _obtener_numero_evento(otrosi_modalidad),
                    'version': getattr(otrosi_modalidad, 'version', 1)
                }
                vista['tiene_modificaciones'] = True
        except Exception:
            # Si hay algún error, continuar sin marcar como modificado
            pass
    
    try:
        canon_minimo, otrosi_canon_min = obtener_valor_campo('nuevo_canon_minimo_garantizado', 'canon_minimo_garantizado')
    except Exception:
        canon_minimo = getattr(contrato, 'canon_minimo_garantizado', None)
        otrosi_canon_min = None
    
    vista['canon_minimo_garantizado'] = canon_minimo
    # Verificar si el Otro Sí realmente modificó el campo:
    # 1. Debe tener un valor no nulo/no vacío en el campo
    # 2. Ese valor debe ser diferente del valor vigente ANTES del Otro Sí
    if otrosi_canon_min and canon_minimo is not None:
        try:
            # Verificar que el campo realmente tenga un valor válido (no None, no 0 para Decimal)
            from decimal import Decimal
            valor_otrosi_decimal = Decimal(str(canon_minimo)) if canon_minimo else None
            if valor_otrosi_decimal is not None and valor_otrosi_decimal != Decimal('0'):
                # Obtener el valor que estaba vigente ANTES de este Otro Sí
                valor_antes_otrosi = obtener_valor_vigente_antes_de_otrosi(otrosi_canon_min, 'canon_minimo_garantizado')
                
                # Comparar valores considerando None y Decimal
                es_diferente = False
                if valor_antes_otrosi is None:
                    es_diferente = True  # Si no había valor antes y ahora sí hay, fue modificado
                elif valor_antes_otrosi is not None:
                    try:
                        # Convertir a Decimal para comparación precisa
                        canon_min_antes = Decimal(str(valor_antes_otrosi)) if valor_antes_otrosi else None
                        if canon_min_antes is not None and valor_otrosi_decimal is not None:
                            es_diferente = canon_min_antes != valor_otrosi_decimal
                    except (ValueError, TypeError):
                        # Si hay error al convertir, comparar directamente
                        es_diferente = valor_antes_otrosi != canon_minimo
                
                if es_diferente:
                    vista['campos_modificados']['canon_minimo_garantizado'] = {
                        'original': valor_antes_otrosi,
                        'nuevo': canon_minimo,
                        'otrosi': _obtener_numero_evento(otrosi_canon_min),
                        'version': getattr(otrosi_canon_min, 'version', 1)
                    }
                    vista['tiene_modificaciones'] = True
        except Exception:
            # Si hay algún error, continuar sin marcar como modificado
            pass
    
    # Considerar cálculos de IPC o Salario Mínimo aplicados hasta la fecha de referencia
    ultimo_calculo_aplicado = None
    try:
        from gestion.utils_ipc import obtener_ultimo_calculo_aplicado_hasta_fecha
        ultimo_calculo_aplicado = obtener_ultimo_calculo_aplicado_hasta_fecha(contrato, fecha_referencia)
    except Exception:
        # Si hay error al obtener el cálculo, continuar sin aplicar cálculos
        pass
    
    if ultimo_calculo_aplicado and hasattr(ultimo_calculo_aplicado, 'nuevo_canon') and ultimo_calculo_aplicado.nuevo_canon:
        # Determinar qué campo actualizar según el tipo de contrato
        aplicar_calculo = False
        
        if contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR':
            # Para proveedores, actualizar "Valor mensual" (canon_minimo_garantizado)
            # Solo aplicar si no hay un Otro Sí que realmente haya modificado el campo después del cálculo
            # Si otrosi_canon_min existe pero no tiene valor válido (None o 0), tratarlo como si no existiera
            otrosi_modifico_realmente = False
            if otrosi_canon_min and canon_minimo is not None:
                from decimal import Decimal
                valor_otrosi_decimal = Decimal(str(canon_minimo)) if canon_minimo else None
                if valor_otrosi_decimal is not None and valor_otrosi_decimal != Decimal('0'):
                    otrosi_modifico_realmente = True
            
            if not otrosi_modifico_realmente:
                # No hay Otro Sí que realmente modificó el campo, aplicar el cálculo
                aplicar_calculo = True
            else:
                # Hay Otro Sí que realmente modificó, verificar si el cálculo es posterior
                try:
                    if otrosi_canon_min and hasattr(otrosi_canon_min, 'fecha_aprobacion') and otrosi_canon_min.fecha_aprobacion:
                        fecha_otrosi = otrosi_canon_min.fecha_aprobacion
                        # Convertir a date si es datetime
                        if hasattr(fecha_otrosi, 'date'):
                            fecha_otrosi = fecha_otrosi.date()
                        elif not isinstance(fecha_otrosi, date):
                            # Si no es date ni datetime, intentar convertir
                            if isinstance(fecha_otrosi, datetime):
                                fecha_otrosi = fecha_otrosi.date()
                            else:
                                aplicar_calculo = True
                                fecha_otrosi = None
                        
                        if fecha_otrosi:
                            # Convertir fecha_aplicacion a date si es necesario
                            fecha_calculo = None
                            if hasattr(ultimo_calculo_aplicado, 'fecha_aplicacion') and ultimo_calculo_aplicado.fecha_aplicacion:
                                fecha_calculo = ultimo_calculo_aplicado.fecha_aplicacion
                                if hasattr(fecha_calculo, 'date'):
                                    fecha_calculo = fecha_calculo.date()
                                elif isinstance(fecha_calculo, datetime):
                                    fecha_calculo = fecha_calculo.date()
                                elif not isinstance(fecha_calculo, date):
                                    aplicar_calculo = True
                                    fecha_calculo = None
                            
                            if fecha_calculo:
                                aplicar_calculo = fecha_calculo >= fecha_otrosi
                            else:
                                aplicar_calculo = True
                        else:
                            aplicar_calculo = True
                    else:
                        # Si no tiene fecha de aprobación, aplicar el cálculo
                        aplicar_calculo = True
                except Exception:
                    # Si hay algún error al comparar fechas, aplicar el cálculo por seguridad
                    aplicar_calculo = True
            
            if aplicar_calculo:
                try:
                    # Usar el valor del cálculo o el valor vigente actual (que puede ser del contrato base)
                    valor_base_para_calculo = canon_minimo if canon_minimo is not None else getattr(contrato, 'canon_minimo_garantizado', None)
                    if ultimo_calculo_aplicado.nuevo_canon is not None:
                        vista['canon_minimo_garantizado'] = ultimo_calculo_aplicado.nuevo_canon
                        if 'canon_minimo_garantizado' not in vista['campos_modificados']:
                            # Determinar el tipo de cálculo de forma segura
                            tipo_calculo = 'Salario Mínimo'
                            try:
                                if hasattr(ultimo_calculo_aplicado, 'ipc_historico'):
                                    if ultimo_calculo_aplicado.ipc_historico is not None:
                                        tipo_calculo = 'IPC'
                            except Exception:
                                pass
                            
                            fecha_calculo_display = None
                            if hasattr(ultimo_calculo_aplicado, 'fecha_aplicacion') and ultimo_calculo_aplicado.fecha_aplicacion:
                                fecha_calculo_display = ultimo_calculo_aplicado.fecha_aplicacion
                                if hasattr(fecha_calculo_display, 'date'):
                                    fecha_calculo_display = fecha_calculo_display.date()
                                elif isinstance(fecha_calculo_display, datetime):
                                    fecha_calculo_display = fecha_calculo_display.date()
                            
                            vista['campos_modificados']['canon_minimo_garantizado'] = {
                                'original': valor_base_para_calculo,
                                'nuevo': ultimo_calculo_aplicado.nuevo_canon,
                                'calculo': True,
                                'tipo_calculo': tipo_calculo,
                                'fecha_calculo': fecha_calculo_display
                            }
                            vista['tiene_modificaciones'] = True
                except Exception:
                    # Si hay algún error, continuar sin aplicar el cálculo
                    pass
        else:
            # Para arrendatarios, actualizar "Canon" (valor_canon)
            # Solo aplicar si no hay un Otro Sí que realmente haya modificado el campo después del cálculo
            # Si otrosi_canon existe pero no tiene valor válido (None o 0), tratarlo como si no existiera
            otrosi_modifico_realmente = False
            if otrosi_canon and valor_canon is not None:
                from decimal import Decimal
                valor_otrosi_decimal = Decimal(str(valor_canon)) if valor_canon else None
                if valor_otrosi_decimal is not None and valor_otrosi_decimal != Decimal('0'):
                    otrosi_modifico_realmente = True
            
            if not otrosi_modifico_realmente:
                # No hay Otro Sí que realmente modificó el campo, aplicar el cálculo
                aplicar_calculo = True
            else:
                # Hay Otro Sí que realmente modificó, verificar si el cálculo es posterior
                try:
                    if otrosi_canon and hasattr(otrosi_canon, 'fecha_aprobacion') and otrosi_canon.fecha_aprobacion:
                        fecha_otrosi = otrosi_canon.fecha_aprobacion
                        # Convertir a date si es datetime
                        if hasattr(fecha_otrosi, 'date'):
                            fecha_otrosi = fecha_otrosi.date()
                        elif not isinstance(fecha_otrosi, date):
                            # Si no es date ni datetime, intentar convertir
                            if isinstance(fecha_otrosi, datetime):
                                fecha_otrosi = fecha_otrosi.date()
                            else:
                                aplicar_calculo = True
                                fecha_otrosi = None
                        
                        if fecha_otrosi:
                            # Convertir fecha_aplicacion a date si es necesario
                            fecha_calculo = None
                            if hasattr(ultimo_calculo_aplicado, 'fecha_aplicacion') and ultimo_calculo_aplicado.fecha_aplicacion:
                                fecha_calculo = ultimo_calculo_aplicado.fecha_aplicacion
                                if hasattr(fecha_calculo, 'date'):
                                    fecha_calculo = fecha_calculo.date()
                                elif isinstance(fecha_calculo, datetime):
                                    fecha_calculo = fecha_calculo.date()
                                elif not isinstance(fecha_calculo, date):
                                    aplicar_calculo = True
                                    fecha_calculo = None
                            
                            if fecha_calculo:
                                aplicar_calculo = fecha_calculo >= fecha_otrosi
                            else:
                                aplicar_calculo = True
                        else:
                            aplicar_calculo = True
                    else:
                        # Si no tiene fecha de aprobación, aplicar el cálculo
                        aplicar_calculo = True
                except Exception:
                    # Si hay algún error al comparar fechas, aplicar el cálculo por seguridad
                    aplicar_calculo = True
            
            if aplicar_calculo:
                try:
                    # Usar el valor del cálculo o el valor vigente actual (que puede ser del contrato base)
                    valor_base_para_calculo = valor_canon if valor_canon is not None else getattr(contrato, 'valor_canon_fijo', None)
                    if ultimo_calculo_aplicado.nuevo_canon is not None:
                        vista['valor_canon'] = ultimo_calculo_aplicado.nuevo_canon
                        if 'valor_canon' not in vista['campos_modificados']:
                            # Determinar el tipo de cálculo de forma segura
                            tipo_calculo = 'Salario Mínimo'
                            try:
                                if hasattr(ultimo_calculo_aplicado, 'ipc_historico'):
                                    if ultimo_calculo_aplicado.ipc_historico is not None:
                                        tipo_calculo = 'IPC'
                            except Exception:
                                pass
                            
                            fecha_calculo_display = None
                            if hasattr(ultimo_calculo_aplicado, 'fecha_aplicacion') and ultimo_calculo_aplicado.fecha_aplicacion:
                                fecha_calculo_display = ultimo_calculo_aplicado.fecha_aplicacion
                                if hasattr(fecha_calculo_display, 'date'):
                                    fecha_calculo_display = fecha_calculo_display.date()
                                elif isinstance(fecha_calculo_display, datetime):
                                    fecha_calculo_display = fecha_calculo_display.date()
                            
                            vista['campos_modificados']['valor_canon'] = {
                                'original': valor_base_para_calculo,
                                'nuevo': ultimo_calculo_aplicado.nuevo_canon,
                                'calculo': True,
                                'tipo_calculo': tipo_calculo,
                                'fecha_calculo': fecha_calculo_display
                            }
                            vista['tiene_modificaciones'] = True
                except Exception:
                    # Si hay algún error, continuar sin aplicar el cálculo
                    pass
    
    try:
        porcentaje_ventas, otrosi_ventas = obtener_valor_campo('nuevo_porcentaje_ventas', 'porcentaje_ventas')
    except Exception:
        porcentaje_ventas = getattr(contrato, 'porcentaje_ventas', None)
        otrosi_ventas = None
    
    vista['porcentaje_ventas'] = porcentaje_ventas
    # Verificar si el Otro Sí realmente modificó el campo:
    # 1. Debe tener un valor no nulo/no vacío en el campo
    # 2. Ese valor debe ser diferente del valor vigente ANTES del Otro Sí
    if otrosi_ventas and porcentaje_ventas is not None:
        try:
            # Verificar que el campo realmente tenga un valor válido (no None, no 0 para Decimal)
            valor_otrosi_decimal = Decimal(str(porcentaje_ventas)) if porcentaje_ventas else None
            if valor_otrosi_decimal is not None and valor_otrosi_decimal != Decimal('0'):
                # Obtener el valor que estaba vigente ANTES de este Otro Sí
                valor_antes_otrosi = obtener_valor_vigente_antes_de_otrosi(otrosi_ventas, 'porcentaje_ventas')
                
                # Comparar valores considerando None y Decimal
                es_diferente = False
                if valor_antes_otrosi is None:
                    es_diferente = True  # Si no había valor antes y ahora sí hay, fue modificado
                elif valor_antes_otrosi is not None:
                    try:
                        # Convertir a Decimal para comparación precisa
                        porcentaje_antes = Decimal(str(valor_antes_otrosi)) if valor_antes_otrosi else None
                        if porcentaje_antes is not None and valor_otrosi_decimal is not None:
                            es_diferente = porcentaje_antes != valor_otrosi_decimal
                    except (ValueError, TypeError):
                        # Si hay error al convertir, comparar directamente
                        es_diferente = valor_antes_otrosi != porcentaje_ventas
                
                if es_diferente:
                    vista['campos_modificados']['porcentaje_ventas'] = {
                        'original': valor_antes_otrosi,
                        'nuevo': porcentaje_ventas,
                        'otrosi': _obtener_numero_evento(otrosi_ventas),
                        'version': getattr(otrosi_ventas, 'version', 1)
                    }
                    vista['tiene_modificaciones'] = True
        except Exception:
            # Si hay algún error, continuar sin marcar como modificado
            pass
    
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
        try:
            fecha_final, otrosi_fecha_final = obtener_valor_campo('nueva_fecha_final_actualizada', 'fecha_final_actualizada')
        except Exception:
            fecha_final = getattr(contrato, 'fecha_final_actualizada', None)
            otrosi_fecha_final = None
        
        if fecha_final is None:
            fecha_final = getattr(contrato, 'fecha_final_inicial', None)
    
    vista['fecha_final_actualizada'] = fecha_final
    if otrosi_fecha_final:
        try:
            vista['campos_modificados']['fecha_final_actualizada'] = {
                'original': contrato.fecha_final_actualizada or contrato.fecha_final_inicial,
                'nuevo': fecha_final,
                'otrosi': _obtener_numero_evento(otrosi_fecha_final),
                'version': otrosi_fecha_final.version
            }
            vista['tiene_modificaciones'] = True
        except Exception:
            pass
    
    try:
        duracion_meses, otrosi_duracion = obtener_valor_campo('nuevo_plazo_meses', 'duracion_inicial_meses')
    except Exception:
        duracion_meses = getattr(contrato, 'duracion_inicial_meses', None)
        otrosi_duracion = None
    
    vista['duracion_meses'] = duracion_meses
    if otrosi_duracion:
        try:
            vista['campos_modificados']['duracion_meses'] = {
                'original': contrato.duracion_inicial_meses,
                'nuevo': duracion_meses,
                'otrosi': _obtener_numero_evento(otrosi_duracion),
                'version': getattr(otrosi_duracion, 'version', 1)
            }
            vista['tiene_modificaciones'] = True
        except Exception:
            pass
    
    # IPC
    try:
        tipo_ipc, otrosi_tipo_ipc = obtener_valor_campo('nuevo_tipo_condicion_ipc', 'tipo_condicion_ipc')
    except Exception:
        tipo_ipc = getattr(contrato, 'tipo_condicion_ipc', None)
        otrosi_tipo_ipc = None
    
    vista['tipo_condicion_ipc'] = tipo_ipc
    if otrosi_tipo_ipc:
        try:
            vista['campos_modificados']['tipo_condicion_ipc'] = {
                'original': contrato.tipo_condicion_ipc,
                'nuevo': tipo_ipc,
                'otrosi': _obtener_numero_evento(otrosi_tipo_ipc),
                'version': getattr(otrosi_tipo_ipc, 'version', 1)
            }
            vista['tiene_modificaciones'] = True
        except Exception:
            pass
    
    try:
        puntos_ipc, otrosi_puntos_ipc = obtener_valor_campo('nuevos_puntos_adicionales_ipc', 'puntos_adicionales_ipc')
    except Exception:
        puntos_ipc = getattr(contrato, 'puntos_adicionales_ipc', None)
        otrosi_puntos_ipc = None
    
    vista['puntos_adicionales_ipc'] = puntos_ipc
    if otrosi_puntos_ipc:
        try:
            vista['campos_modificados']['puntos_adicionales_ipc'] = {
                'original': contrato.puntos_adicionales_ipc,
                'nuevo': puntos_ipc,
                'otrosi': _obtener_numero_evento(otrosi_puntos_ipc),
                'version': getattr(otrosi_puntos_ipc, 'version', 1)
            }
            vista['tiene_modificaciones'] = True
        except Exception:
            pass
    
    try:
        periodicidad_ipc, otrosi_periodicidad = obtener_valor_campo('nueva_periodicidad_ipc', 'periodicidad_ipc')
    except Exception:
        periodicidad_ipc = getattr(contrato, 'periodicidad_ipc', None)
        otrosi_periodicidad = None
    
    vista['periodicidad_ipc'] = periodicidad_ipc
    if otrosi_periodicidad:
        try:
            vista['campos_modificados']['periodicidad_ipc'] = {
                'original': contrato.periodicidad_ipc,
                'nuevo': periodicidad_ipc,
                'otrosi': _obtener_numero_evento(otrosi_periodicidad),
                'version': getattr(otrosi_periodicidad, 'version', 1)
            }
            vista['tiene_modificaciones'] = True
        except Exception:
            pass
    
    try:
        fecha_aumento_ipc, otrosi_fecha_ipc = obtener_valor_campo('nueva_fecha_aumento_ipc', 'fecha_aumento_ipc')
    except Exception:
        fecha_aumento_ipc = getattr(contrato, 'fecha_aumento_ipc', None)
        otrosi_fecha_ipc = None
    
    vista['fecha_aumento_ipc'] = fecha_aumento_ipc
    if otrosi_fecha_ipc:
        try:
            vista['campos_modificados']['fecha_aumento_ipc'] = {
                'original': contrato.fecha_aumento_ipc,
                'nuevo': fecha_aumento_ipc,
                'otrosi': _obtener_numero_evento(otrosi_fecha_ipc),
                'version': getattr(otrosi_fecha_ipc, 'version', 1)
            }
            vista['tiene_modificaciones'] = True
        except Exception:
            pass
    
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
                valor_contrato = getattr(contrato, campo_contrato, None)
                return valor_contrato, None
            
            es_vigente = otrosi_modificador.effective_from <= fecha_referencia
            if otrosi_modificador.effective_to is not None:
                es_vigente = es_vigente and otrosi_modificador.effective_to >= fecha_referencia
            
            if es_vigente:
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
        
        # Si no hay Otro Sí que lo modificó o el evento no es vigente, usar valor del contrato
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
    # Verificar explícitamente que no haya eventos futuros que modifiquen este campo
    exige_rce, otrosi_exige_rce = obtener_bool_y_otrosi('nuevo_exige_poliza_rce', 'exige_poliza_rce')
    # Si hay un modificador pero no es vigente, usar el valor del contrato base
    if otrosi_exige_rce:
        # Verificar nuevamente la vigencia del modificador
        if otrosi_exige_rce.effective_from > fecha_referencia:
            # El evento es futuro, usar valor del contrato base
            exige_rce = getattr(contrato, 'exige_poliza_rce', False)
        elif otrosi_exige_rce.effective_to is not None and otrosi_exige_rce.effective_to < fecha_referencia:
            # El evento ya venció, usar valor del contrato base
            exige_rce = getattr(contrato, 'exige_poliza_rce', False)
    
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
    # Verificar explícitamente que no haya eventos futuros que modifiquen este campo
    exige_cumplimiento, otrosi_exige_cumplimiento = obtener_bool_y_otrosi('nuevo_exige_poliza_cumplimiento', 'exige_poliza_cumplimiento')
    # Si hay un modificador pero no es vigente, usar el valor del contrato base
    if otrosi_exige_cumplimiento:
        # Verificar nuevamente la vigencia del modificador
        if otrosi_exige_cumplimiento.effective_from > fecha_referencia:
            # El evento es futuro, usar valor del contrato base
            exige_cumplimiento = getattr(contrato, 'exige_poliza_cumplimiento', False)
        elif otrosi_exige_cumplimiento.effective_to is not None and otrosi_exige_cumplimiento.effective_to < fecha_referencia:
            # El evento ya venció, usar valor del contrato base
            exige_cumplimiento = getattr(contrato, 'exige_poliza_cumplimiento', False)
    
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
    # Verificar explícitamente que no haya eventos futuros que modifiquen este campo
    exige_arrendamiento, otrosi_exige_arrendamiento = obtener_bool_y_otrosi('nuevo_exige_poliza_arrendamiento', 'exige_poliza_arrendamiento')
    # Si hay un modificador pero no es vigente, usar el valor del contrato base
    if otrosi_exige_arrendamiento:
        # Verificar nuevamente la vigencia del modificador
        if otrosi_exige_arrendamiento.effective_from > fecha_referencia:
            # El evento es futuro, usar valor del contrato base
            exige_arrendamiento = getattr(contrato, 'exige_poliza_arrendamiento', False)
        elif otrosi_exige_arrendamiento.effective_to is not None and otrosi_exige_arrendamiento.effective_to < fecha_referencia:
            # El evento ya venció, usar valor del contrato base
            exige_arrendamiento = getattr(contrato, 'exige_poliza_arrendamiento', False)
    
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
    # Verificar explícitamente que no haya eventos futuros que modifiquen este campo
    exige_todo_riesgo, otrosi_exige_todo_riesgo = obtener_bool_y_otrosi('nuevo_exige_poliza_todo_riesgo', 'exige_poliza_todo_riesgo')
    # Si hay un modificador pero no es vigente, usar el valor del contrato base
    if otrosi_exige_todo_riesgo:
        # Verificar nuevamente la vigencia del modificador
        if otrosi_exige_todo_riesgo.effective_from > fecha_referencia:
            # El evento es futuro, usar valor del contrato base
            exige_todo_riesgo = getattr(contrato, 'exige_poliza_todo_riesgo', False)
        elif otrosi_exige_todo_riesgo.effective_to is not None and otrosi_exige_todo_riesgo.effective_to < fecha_referencia:
            # El evento ya venció, usar valor del contrato base
            exige_todo_riesgo = getattr(contrato, 'exige_poliza_todo_riesgo', False)
    
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
    # Verificar explícitamente que no haya eventos futuros que modifiquen este campo
    exige_otra, otrosi_exige_otra = obtener_bool_y_otrosi('nuevo_exige_poliza_otra_1', 'exige_poliza_otra_1')
    # Si hay un modificador pero no es vigente, usar el valor del contrato base
    if otrosi_exige_otra:
        # Verificar nuevamente la vigencia del modificador
        if otrosi_exige_otra.effective_from > fecha_referencia:
            # El evento es futuro, usar valor del contrato base
            exige_otra = getattr(contrato, 'exige_poliza_otra_1', False)
        elif otrosi_exige_otra.effective_to is not None and otrosi_exige_otra.effective_to < fecha_referencia:
            # El evento ya venció, usar valor del contrato base
            exige_otra = getattr(contrato, 'exige_poliza_otra_1', False)
    
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
    
    # IMPORTANTE: NO modificar los campos de pólizas del contrato base.
    # Los valores de pólizas deben estar solo en la renovación automática
    # y obtenerse mediante el efecto cadena en get_polizas_requeridas_contrato.
    # Esto permite que la vista vigente muestre correctamente el estado histórico
    # del contrato según la fecha de referencia seleccionada.
    
    contrato.save()
    
    return renovacion

