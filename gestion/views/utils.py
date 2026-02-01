from datetime import date

from django.http import HttpResponse
from django.utils import timezone

from gestion.models import ConfiguracionEmpresa, SeguimientoContrato, SeguimientoPoliza
from gestion.forms import DEFAULT_EMPRESA_CONFIG
from gestion.utils import calcular_meses_vigencia


def _aplicar_polizas_vigentes_a_requisitos(requisitos, polizas_queryset, sobrescribir=False):
    """
    Fusiona la información de pólizas vigentes (generalmente asociadas a un Otro Sí)
    dentro de la estructura de requisitos requerida por el formulario.
    
    Args:
        requisitos: Diccionario con los requisitos base
        polizas_queryset: QuerySet de pólizas vigentes
        sobrescribir: Si True, sobrescribe valores existentes. Si False, solo llena valores vacíos.
    """
    if not requisitos:
        return requisitos

    if not polizas_queryset:
        return requisitos

    tipo_map = {
        'RCE - Responsabilidad Civil': 'rce',
        'Cumplimiento': 'cumplimiento',
        'Poliza de Arrendamiento': 'arrendamiento',
        'Arrendamiento': 'todo_riesgo',
        'Otra': 'otra',
    }

    def _score_poliza(item):
        return (
            1 if getattr(item, 'otrosi_id', None) else 0,
            getattr(item, 'fecha_vencimiento', None) or date.min,
            getattr(item, 'fecha_inicio_vigencia', None) or date.min,
            item.pk or 0,
        )

    polizas_ordenadas = sorted(polizas_queryset, key=_score_poliza, reverse=True)

    poliza_por_tipo = {}
    for poliza in polizas_ordenadas:
        clave = tipo_map.get(poliza.tipo)
        if not clave or clave not in requisitos:
            continue

        if clave not in poliza_por_tipo:
            poliza_por_tipo[clave] = poliza

    detalles_map = {
        'rce': {
            'valor_propietario_locatario_ocupante_rce': 'plo',
            'valor_patronal_rce': 'patronal',
            'valor_gastos_medicos_rce': 'gastos_medicos',
            'valor_vehiculos_rce': 'vehiculos',
            'valor_contratistas_rce': 'contratistas',
            'valor_perjuicios_extrapatrimoniales_rce': 'perjuicios',
            'valor_dano_moral_rce': 'dano_moral',
            'valor_lucro_cesante_rce': 'lucro_cesante',
        },
        'cumplimiento': {
            'valor_remuneraciones_cumplimiento': 'remuneraciones',
            'valor_servicios_publicos_cumplimiento': 'servicios_publicos',
            'valor_iva_cumplimiento': 'iva',
            'valor_otros_cumplimiento': 'cuota_admon',
        },
        'arrendamiento': {
            'valor_remuneraciones_arrendamiento': 'remuneraciones',
            'valor_servicios_publicos_arrendamiento': 'servicios_publicos',
            'valor_iva_arrendamiento': 'iva',
            'valor_otros_arrendamiento': 'cuota_admon',
        },
    }

    for clave, poliza in poliza_por_tipo.items():
        destino = requisitos[clave]
        destino['fuente'] = 'otrosi'
        destino['poliza_origen'] = poliza
        destino.setdefault('detalles', {})

        if hasattr(poliza, 'valor_asegurado') and poliza.valor_asegurado is not None:
            destino['valor'] = poliza.valor_asegurado

        if poliza.fecha_inicio_vigencia and poliza.fecha_vencimiento:
            try:
                destino['vigencia'] = calcular_meses_vigencia(poliza.fecha_inicio_vigencia, poliza.fecha_vencimiento)
            except Exception:
                destino['vigencia'] = destino.get('vigencia')
            destino['fecha_fin'] = poliza.fecha_vencimiento

        mapa_detalles = detalles_map.get(clave)
        if mapa_detalles:
            for attr_modelo, llave_detalle in mapa_detalles.items():
                valor_detalle = getattr(poliza, attr_modelo, None)
                if valor_detalle not in [None, '']:
                    if sobrescribir or getattr(poliza, 'otrosi_id', None):
                        destino['detalles'][llave_detalle] = valor_detalle
                    else:
                        detalle_actual = destino['detalles'].get(llave_detalle)
                        if detalle_actual in [None, '']:
                            destino['detalles'][llave_detalle] = valor_detalle

        if clave == 'otra' and getattr(poliza, 'otrosi', None):
            destino['nombre'] = getattr(poliza, 'numero_poliza', destino.get('nombre'))

    for poliza in polizas_ordenadas:
        clave = tipo_map.get(poliza.tipo)
        if not clave or clave not in requisitos:
            continue

        destino = requisitos[clave]
        destino.setdefault('detalles', {})

        mapa_detalles = detalles_map.get(clave)
        if not mapa_detalles:
            continue

        for attr_modelo, llave_detalle in mapa_detalles.items():
            valor_detalle = getattr(poliza, attr_modelo, None)
            if valor_detalle not in [None, '']:
                detalle_actual = destino['detalles'].get(llave_detalle)
                if sobrescribir or getattr(poliza, 'otrosi_id', None) or detalle_actual in [None, '']:
                    destino['detalles'][llave_detalle] = valor_detalle

    return requisitos


def _construir_requisitos_poliza(contrato, vista_vigente, permitir_fuera_vigencia=False):
    """
    Construye los requisitos de pólizas considerando el último Otro Sí vigente que afecte pólizas.
    
    Usa la función get_polizas_requeridas_contrato que ya maneja los valores del OtroSi vigente
    cuando modifica_polizas=True, manteniendo independencia entre contrato base y OtroSi.
    
    Args:
        contrato: Instancia del modelo Contrato
        vista_vigente: Diccionario con la vista vigente del contrato
        permitir_fuera_vigencia: Si es True, permite obtener requisitos incluso si el contrato
                                 aún no ha iniciado. Útil para gestionar pólizas antes del inicio.
    """
    from gestion.utils_otrosi import get_polizas_requeridas_contrato
    
    fecha_referencia = vista_vigente.get('fecha_referencia', date.today())
    
    polizas_requeridas = get_polizas_requeridas_contrato(contrato, fecha_referencia, permitir_fuera_vigencia)
    
    otrosi_vigente = vista_vigente.get('otrosi_vigente')
    fuente = 'otrosi' if (otrosi_vigente and otrosi_vigente.modifica_polizas) else 'contrato'
    
    requisitos = {
        'rce': {
            'exigida': False,
            'valor': None,
            'vigencia': None,
            'fecha_inicio': None,
            'fecha_fin': None,
            'fuente': fuente,
            'detalles': {}
        },
        'cumplimiento': {
            'exigida': False,
            'valor': None,
            'vigencia': None,
            'fecha_inicio': None,
            'fecha_fin': None,
            'fuente': fuente,
            'detalles': {}
        },
        'arrendamiento': {
            'exigida': False,
            'valor': None,
            'vigencia': None,
            'fecha_inicio': None,
            'fecha_fin': None,
            'fuente': fuente,
            'detalles': {}
        },
        'todo_riesgo': {
            'exigida': False,
            'valor': None,
            'vigencia': None,
            'fecha_inicio': None,
            'fecha_fin': None,
            'fuente': fuente,
            'detalles': {}
        },
        'otra': {
            'exigida': False,
            'nombre': None,
            'valor': None,
            'vigencia': None,
            'fecha_inicio': None,
            'fecha_fin': None,
            'fuente': fuente,
            'detalles': {}
        }
    }
    
    mapeo_polizas = {
        'RCE - Responsabilidad Civil': ('rce', {}),
        'Cumplimiento': ('cumplimiento', {}),
        'Poliza de Arrendamiento': ('arrendamiento', {}),
        'Arrendamiento': ('todo_riesgo', {}),
        'Otra': ('otra', {'nombre': None}),
    }
    
    for tipo_poliza, (clave_requisito, extras) in mapeo_polizas.items():
        if tipo_poliza in polizas_requeridas:
            pol_data = polizas_requeridas[tipo_poliza]
            otrosi_modificador = pol_data.get('otrosi_modificador')
            # Si hay un Otro Sí modificador, usar 'otrosi' como fuente, sino usar la fuente general
            fuente_poliza = 'otrosi' if otrosi_modificador else fuente
            requisitos[clave_requisito] = {
                'exigida': True,
                'valor': pol_data.get('valor_requerido'),
                'vigencia': pol_data.get('meses_vigencia'),
                'fecha_inicio': pol_data.get('fecha_inicio_requerida'),
                'fecha_fin': pol_data.get('fecha_fin_requerida'),
                'fuente': fuente_poliza,
                'otrosi_modificador': otrosi_modificador,
                'detalles': pol_data.get('detalles', {}),
                **extras
            }
            if tipo_poliza == 'Otra':
                requisitos[clave_requisito]['nombre'] = pol_data.get('nombre')

    return requisitos


def obtener_configuracion_empresa():
    """Obtiene la configuración vigente de la empresa."""
    configuracion = ConfiguracionEmpresa.objects.filter(activo=True).order_by('-fecha_creacion').first()
    if configuracion:
        return configuracion

    configuracion = ConfiguracionEmpresa.objects.order_by('-fecha_creacion').first()
    if configuracion:
        return configuracion

    return ConfiguracionEmpresa.objects.create(
        **DEFAULT_EMPRESA_CONFIG,
        activo=True,
    )


def registrar_seguimientos_contrato_desde_formulario(form, contrato, usuario):
    """Registra los seguimientos diligenciados en el formulario de contrato."""
    usuario_registro = usuario if usuario else None

    detalle_general = form.cleaned_data.get('seguimiento_general', '')
    if detalle_general and detalle_general.strip():
        SeguimientoContrato.objects.create(
            contrato=contrato,
            detalle=detalle_general.strip(),
            registrado_por=usuario_registro
        )

    campos_poliza = [
        ('seguimiento_poliza_rce', 'RCE - Responsabilidad Civil'),
        ('seguimiento_poliza_cumplimiento', 'Cumplimiento'),
        ('seguimiento_poliza_arrendamiento', 'Poliza de Arrendamiento'),
        ('seguimiento_poliza_todo_riesgo', 'Arrendamiento'),
        ('seguimiento_poliza_otra', 'Otra'),
    ]

    for campo, tipo in campos_poliza:
        detalle = form.cleaned_data.get(campo, '')
        if detalle and detalle.strip():
            SeguimientoPoliza.objects.create(
                contrato=contrato,
                poliza_tipo=tipo,
                detalle=detalle.strip(),
                registrado_por=usuario_registro
            )


def _respuesta_archivo_excel(contenido: bytes, nombre_base: str) -> HttpResponse:
    ahora_local = timezone.localtime(timezone.now())
    marca_tiempo = ahora_local.strftime('%Y%m%d_%H%M%S')
    nombre_archivo = f'{nombre_base}_{marca_tiempo}.xlsx'
    respuesta = HttpResponse(
        contenido,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return respuesta


def _obtener_fecha_final_contrato(contrato, fecha_referencia=None):
    """Obtiene la fecha final del contrato considerando Otrosí y Renovaciones Automáticas vigentes usando efecto cadena"""
    from gestion.utils_otrosi import get_otrosi_vigente, get_ultimo_otrosi_que_modifico_campo_hasta_fecha
    from gestion.models import RenovacionAutomatica
    
    if fecha_referencia is None:
        fecha_referencia = date.today()
    
    # Primero verificar si hay una Renovación Automática vigente (tiene prioridad sobre Otrosí)
    renovacion_vigente = RenovacionAutomatica.objects.filter(
        contrato=contrato,
        estado='APROBADO',
        effective_from__lte=fecha_referencia
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
    # Considerar tanto Otrosí como Renovaciones Automáticas
    otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato, 'nueva_fecha_final_actualizada', fecha_referencia
    )
    renovacion_modificadora = RenovacionAutomatica.objects.filter(
        contrato=contrato,
        estado='APROBADO',
        nueva_fecha_final_actualizada__isnull=False,
        effective_from__lte=fecha_referencia
    ).order_by('-effective_from', '-fecha_aprobacion', '-version').first()
    
    # Determinar cuál es más reciente (otrosí o renovación)
    fecha_final = None
    if otrosi_modificador and otrosi_modificador.nueva_fecha_final_actualizada:
        fecha_final = otrosi_modificador.nueva_fecha_final_actualizada
    if renovacion_modificadora and renovacion_modificadora.nueva_fecha_final_actualizada:
        # Si hay renovación y es más reciente que otrosí, usar renovación
        if not fecha_final or (renovacion_modificadora.effective_from >= (otrosi_modificador.effective_from if otrosi_modificador else date.min)):
            fecha_final = renovacion_modificadora.nueva_fecha_final_actualizada
    
    if fecha_final:
        return fecha_final
    
    # Si no hay modificaciones, usar fecha final del contrato (NO fecha_final_actualizada que puede estar desactualizada)
    return contrato.fecha_final_inicial


def _es_contrato_vencido(contrato, fecha_referencia=None):
    """Determina si un contrato está vencido considerando Otrosí vigentes"""
    if fecha_referencia is None:
        fecha_referencia = date.today()
    
    fecha_final = _obtener_fecha_final_contrato(contrato, fecha_referencia)
    return fecha_final < fecha_referencia


def procesar_polizas_del_formulario(request, contrato):
    """Procesa las pólizas enviadas desde el formulario dinámico"""
    from gestion.models import Poliza
    from datetime import timedelta
    
    polizas_creadas = 0
    
    i = 0
    while True:
        tipo_key = f'poliza_{i}_tipo'
        valor_key = f'poliza_{i}_valor'
        vigencia_key = f'poliza_{i}_vigencia'
        
        if tipo_key in request.POST:
            tipo = request.POST.get(tipo_key)
            valor = request.POST.get(valor_key)
            vigencia = request.POST.get(vigencia_key)
            
            if tipo and valor and vigencia:
                try:
                    import re
                    valor_limpio = re.sub(r'[^\d]', '', valor)
                    
                    poliza = Poliza.objects.create(
                        contrato=contrato,
                        tipo=tipo,
                        numero_poliza=f'AUTO-{contrato.num_contrato}-{i+1}',
                        valor_asegurado=float(valor_limpio),
                        fecha_vencimiento=date.today() + timedelta(days=30 * int(vigencia)),
                        estado_aportado='No Aportada',
                        aseguradora='Por definir',
                        cobertura=f'Cobertura {tipo}',
                        condiciones=f'Condiciones para {tipo}',
                        garantias=f'Garantias para {tipo}'
                    )
                    polizas_creadas += 1
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error("Error al crear póliza automática en utils", exc_info=True)
            
            i += 1
        else:
            break
    
    if polizas_creadas > 0:
        from django.contrib import messages
        messages.info(request, f'Se crearon {polizas_creadas} polizas requeridas para el contrato.')

