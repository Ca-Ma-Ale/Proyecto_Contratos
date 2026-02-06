from datetime import date, timedelta

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


def _construir_requisitos_poliza_desde_contrato_base(contrato):
    """
    Construye los requisitos de pólizas usando SOLO los valores del contrato base,
    sin considerar ningún Otro Sí o Renovación Automática.
    
    Args:
        contrato: Instancia del modelo Contrato
    
    Returns:
        Diccionario con los requisitos de pólizas del contrato base
    """
    from gestion.utils import calcular_fecha_vencimiento
    
    # Función auxiliar para obtener valor o None
    def get_valor(campo):
        valor = getattr(contrato, campo, None)
        return float(valor) if valor else None
    
    # Función auxiliar para obtener valor o 0
    def get_valor_default(campo, default=0):
        valor = getattr(contrato, campo, None)
        return float(valor) if valor else default
    
    requisitos = {
        'rce': {
            'exigida': getattr(contrato, 'exige_poliza_rce', False) or False,
            'valor': get_valor('valor_asegurado_rce'),
            'vigencia': getattr(contrato, 'meses_vigencia_rce', None),
            'fecha_inicio': getattr(contrato, 'fecha_inicio_vigencia_rce', None) or contrato.fecha_inicio,
            'fecha_fin': getattr(contrato, 'fecha_fin_vigencia_rce', None) or (
                calcular_fecha_vencimiento(contrato.fecha_inicio, getattr(contrato, 'meses_vigencia_rce', None)) 
                if (contrato.fecha_inicio and getattr(contrato, 'meses_vigencia_rce', None)) else None
            ),
            'fuente': 'contrato',
            'detalles': {
                'plo': get_valor_default('valor_propietario_locatario_ocupante_rce'),
                'patronal': get_valor_default('valor_patronal_rce'),
                'gastos_medicos': get_valor_default('valor_gastos_medicos_rce'),
                'vehiculos': get_valor_default('valor_vehiculos_rce'),
                'contratistas': get_valor_default('valor_contratistas_rce'),
                'perjuicios': get_valor_default('valor_perjuicios_extrapatrimoniales_rce'),
                'dano_moral': get_valor_default('valor_dano_moral_rce'),
                'lucro_cesante': get_valor_default('valor_lucro_cesante_rce'),
                'danos_materiales': get_valor_default('rce_cobertura_danos_materiales'),
                'lesiones_personales': get_valor_default('rce_cobertura_lesiones_personales'),
                'muerte_terceros': get_valor_default('rce_cobertura_muerte_terceros'),
                'danos_bienes_terceros': get_valor_default('rce_cobertura_danos_bienes_terceros'),
                'responsabilidad_patronal': get_valor_default('rce_cobertura_responsabilidad_patronal'),
                'responsabilidad_cruzada': get_valor_default('rce_cobertura_responsabilidad_cruzada'),
                'danos_contratistas': get_valor_default('rce_cobertura_danos_contratistas'),
                'danos_ejecucion_contrato': get_valor_default('rce_cobertura_danos_ejecucion_contrato'),
                'danos_predios_vecinos': get_valor_default('rce_cobertura_danos_predios_vecinos'),
                'gastos_medicos_cobertura': get_valor_default('rce_cobertura_gastos_medicos'),
                'gastos_defensa': get_valor_default('rce_cobertura_gastos_defensa'),
                'perjuicios_patrimoniales': get_valor_default('rce_cobertura_perjuicios_patrimoniales'),
            }
        },
        'cumplimiento': {
            'exigida': getattr(contrato, 'exige_poliza_cumplimiento', False) or False,
            'valor': get_valor('valor_asegurado_cumplimiento'),
            'vigencia': getattr(contrato, 'meses_vigencia_cumplimiento', None),
            'fecha_inicio': getattr(contrato, 'fecha_inicio_vigencia_cumplimiento', None) or contrato.fecha_inicio,
            'fecha_fin': getattr(contrato, 'fecha_fin_vigencia_cumplimiento', None) or (
                calcular_fecha_vencimiento(contrato.fecha_inicio, getattr(contrato, 'meses_vigencia_cumplimiento', None)) 
                if (contrato.fecha_inicio and getattr(contrato, 'meses_vigencia_cumplimiento', None)) else None
            ),
            'fuente': 'contrato',
            'detalles': {
                'remuneraciones': get_valor_default('valor_remuneraciones_cumplimiento'),
                'servicios_publicos': get_valor_default('valor_servicios_publicos_cumplimiento'),
                'iva': get_valor_default('valor_iva_cumplimiento'),
                'cuota_admon': get_valor_default('valor_otros_cumplimiento'),
                'cumplimiento_contrato': get_valor_default('cumplimiento_amparo_cumplimiento_contrato'),
                'buen_manejo_anticipo': get_valor_default('cumplimiento_amparo_buen_manejo_anticipo'),
                'amortizacion_anticipo': get_valor_default('cumplimiento_amparo_amortizacion_anticipo'),
                'salarios_prestaciones': get_valor_default('cumplimiento_amparo_salarios_prestaciones'),
                'aportes_seguridad_social': get_valor_default('cumplimiento_amparo_aportes_seguridad_social'),
                'calidad_servicio': get_valor_default('cumplimiento_amparo_calidad_servicio'),
                'estabilidad_obra': get_valor_default('cumplimiento_amparo_estabilidad_obra'),
                'calidad_bienes': get_valor_default('cumplimiento_amparo_calidad_bienes'),
                'multas': get_valor_default('cumplimiento_amparo_multas'),
                'clausula_penal': get_valor_default('cumplimiento_amparo_clausula_penal'),
                'sanciones_incumplimiento': get_valor_default('cumplimiento_amparo_sanciones_incumplimiento'),
            }
        },
        'arrendamiento': {
            'exigida': getattr(contrato, 'exige_poliza_arrendamiento', False) or False,
            'valor': get_valor('valor_asegurado_arrendamiento'),
            'vigencia': getattr(contrato, 'meses_vigencia_arrendamiento', None),
            'fecha_inicio': getattr(contrato, 'fecha_inicio_vigencia_arrendamiento', None) or contrato.fecha_inicio,
            'fecha_fin': getattr(contrato, 'fecha_fin_vigencia_arrendamiento', None) or (
                calcular_fecha_vencimiento(contrato.fecha_inicio, getattr(contrato, 'meses_vigencia_arrendamiento', None)) 
                if (contrato.fecha_inicio and getattr(contrato, 'meses_vigencia_arrendamiento', None)) else None
            ),
            'fuente': 'contrato',
            'detalles': {
                'remuneraciones': get_valor_default('valor_remuneraciones_arrendamiento'),
                'servicios_publicos': get_valor_default('valor_servicios_publicos_arrendamiento'),
                'iva': get_valor_default('valor_iva_arrendamiento'),
                'cuota_admon': get_valor_default('valor_otros_arrendamiento'),
            }
        },
        'todo_riesgo': {
            'exigida': getattr(contrato, 'exige_poliza_todo_riesgo', False) or False,
            'valor': get_valor('valor_asegurado_todo_riesgo'),
            'vigencia': getattr(contrato, 'meses_vigencia_todo_riesgo', None),
            'fecha_inicio': getattr(contrato, 'fecha_inicio_vigencia_todo_riesgo', None) or contrato.fecha_inicio,
            'fecha_fin': getattr(contrato, 'fecha_fin_vigencia_todo_riesgo', None) or (
                calcular_fecha_vencimiento(contrato.fecha_inicio, getattr(contrato, 'meses_vigencia_todo_riesgo', None)) 
                if (contrato.fecha_inicio and getattr(contrato, 'meses_vigencia_todo_riesgo', None)) else None
            ),
            'fuente': 'contrato',
            'detalles': {}
        },
        'otra': {
            'exigida': getattr(contrato, 'exige_poliza_otra_1', False) or False,
            'nombre': getattr(contrato, 'nombre_poliza_otra_1', None),
            'valor': get_valor('valor_asegurado_otra_1'),
            'vigencia': getattr(contrato, 'meses_vigencia_otra_1', None),
            'fecha_inicio': getattr(contrato, 'fecha_inicio_vigencia_otra_1', None) or contrato.fecha_inicio,
            'fecha_fin': getattr(contrato, 'fecha_fin_vigencia_otra_1', None) or (
                calcular_fecha_vencimiento(contrato.fecha_inicio, getattr(contrato, 'meses_vigencia_otra_1', None)) 
                if (contrato.fecha_inicio and getattr(contrato, 'meses_vigencia_otra_1', None)) else None
            ),
            'fuente': 'contrato',
            'detalles': {}
        }
    }
    
    return requisitos


def _construir_requisitos_poliza_desde_otrosi(contrato, otrosi):
    """
    Construye los requisitos de pólizas usando los valores del Otro Sí específico.
    Si un campo no está definido en el Otro Sí, usa el efecto cadena hasta antes del Otro Sí.
    
    Args:
        contrato: Instancia del modelo Contrato
        otrosi: Instancia del modelo OtroSi
    
    Returns:
        Diccionario con los requisitos de pólizas del Otro Sí
    """
    from gestion.utils import calcular_fecha_vencimiento
    from gestion.utils_otrosi import get_polizas_requeridas_contrato
    
    # Obtener valores base usando efecto cadena hasta antes del Otro Sí
    fecha_antes_otrosi = otrosi.effective_from - timedelta(days=1) if otrosi.effective_from else date.today()
    valores_base = get_polizas_requeridas_contrato(contrato, fecha_antes_otrosi, permitir_fuera_vigencia=True)
    
    # Función auxiliar para obtener valor del Otro Sí o del base
    def get_valor_otrosi_o_base(campo_otrosi, clave_poliza=None, campo_base=None):
        valor_otrosi = getattr(otrosi, campo_otrosi, None)
        if valor_otrosi is not None:
            return valor_otrosi
        # Si no está definido en el Otro Sí, usar valor base
        if clave_poliza and clave_poliza in valores_base:
            return valores_base[clave_poliza].get(campo_base) if campo_base else None
        return None
    
    # Función auxiliar para obtener valor o None
    def get_valor(campo):
        valor = getattr(otrosi, campo, None)
        return float(valor) if valor else None
    
    # Función auxiliar para obtener valor o 0
    def get_valor_default(campo, default=0):
        valor = getattr(otrosi, campo, None)
        return float(valor) if valor else default
    
    requisitos = {
        'rce': {
            'exigida': getattr(otrosi, 'nuevo_exige_poliza_rce', None) if getattr(otrosi, 'nuevo_exige_poliza_rce', None) is not None else (valores_base.get('RCE - Responsabilidad Civil', {}).get('valor_requerido') is not None),
            'valor': get_valor('nuevo_valor_asegurado_rce') or (float(valores_base.get('RCE - Responsabilidad Civil', {}).get('valor_requerido', 0)) if valores_base.get('RCE - Responsabilidad Civil', {}).get('valor_requerido') else None),
            'vigencia': getattr(otrosi, 'nuevo_meses_vigencia_rce', None) or valores_base.get('RCE - Responsabilidad Civil', {}).get('meses_vigencia'),
            'fecha_inicio': getattr(otrosi, 'nuevo_fecha_inicio_vigencia_rce', None) or valores_base.get('RCE - Responsabilidad Civil', {}).get('fecha_inicio_requerida'),
            'fecha_fin': getattr(otrosi, 'nuevo_fecha_fin_vigencia_rce', None) or valores_base.get('RCE - Responsabilidad Civil', {}).get('fecha_fin_requerida'),
            'fuente': 'otrosi',
            'detalles': {
                'plo': get_valor_default('nuevo_valor_propietario_locatario_ocupante_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('plo', 0) or 0),
                'patronal': get_valor_default('nuevo_valor_patronal_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('patronal', 0) or 0),
                'gastos_medicos': get_valor_default('nuevo_valor_gastos_medicos_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('gastos_medicos', 0) or 0),
                'vehiculos': get_valor_default('nuevo_valor_vehiculos_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('vehiculos', 0) or 0),
                'contratistas': get_valor_default('nuevo_valor_contratistas_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('contratistas', 0) or 0),
                'perjuicios': get_valor_default('nuevo_valor_perjuicios_extrapatrimoniales_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('perjuicios', 0) or 0),
                'dano_moral': get_valor_default('nuevo_valor_dano_moral_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('dano_moral', 0) or 0),
                'lucro_cesante': get_valor_default('nuevo_valor_lucro_cesante_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('lucro_cesante', 0) or 0),
                'danos_materiales': get_valor_default('nuevo_rce_cobertura_danos_materiales') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('danos_materiales', 0) or 0),
                'lesiones_personales': get_valor_default('nuevo_rce_cobertura_lesiones_personales') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('lesiones_personales', 0) or 0),
                'muerte_terceros': get_valor_default('nuevo_rce_cobertura_muerte_terceros') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('muerte_terceros', 0) or 0),
                'danos_bienes_terceros': get_valor_default('nuevo_rce_cobertura_danos_bienes_terceros') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('danos_bienes_terceros', 0) or 0),
                'responsabilidad_patronal': get_valor_default('nuevo_rce_cobertura_responsabilidad_patronal') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('responsabilidad_patronal', 0) or 0),
                'responsabilidad_cruzada': get_valor_default('nuevo_rce_cobertura_responsabilidad_cruzada') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('responsabilidad_cruzada', 0) or 0),
                'danos_contratistas': get_valor_default('nuevo_rce_cobertura_danos_contratistas') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('danos_contratistas', 0) or 0),
                'danos_ejecucion_contrato': get_valor_default('nuevo_rce_cobertura_danos_ejecucion_contrato') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('danos_ejecucion_contrato', 0) or 0),
                'danos_predios_vecinos': get_valor_default('nuevo_rce_cobertura_danos_predios_vecinos') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('danos_predios_vecinos', 0) or 0),
                'gastos_medicos_cobertura': get_valor_default('nuevo_rce_cobertura_gastos_medicos') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('gastos_medicos_cobertura', 0) or 0),
                'gastos_defensa': get_valor_default('nuevo_rce_cobertura_gastos_defensa') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('gastos_defensa', 0) or 0),
                'perjuicios_patrimoniales': get_valor_default('nuevo_rce_cobertura_perjuicios_patrimoniales') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('perjuicios_patrimoniales', 0) or 0),
            }
        },
        'cumplimiento': {
            'exigida': getattr(otrosi, 'nuevo_exige_poliza_cumplimiento', None) if getattr(otrosi, 'nuevo_exige_poliza_cumplimiento', None) is not None else (valores_base.get('Cumplimiento', {}).get('valor_requerido') is not None),
            'valor': get_valor('nuevo_valor_asegurado_cumplimiento') or (float(valores_base.get('Cumplimiento', {}).get('valor_requerido', 0)) if valores_base.get('Cumplimiento', {}).get('valor_requerido') else None),
            'vigencia': getattr(otrosi, 'nuevo_meses_vigencia_cumplimiento', None) or valores_base.get('Cumplimiento', {}).get('meses_vigencia'),
            'fecha_inicio': getattr(otrosi, 'nuevo_fecha_inicio_vigencia_cumplimiento', None) or valores_base.get('Cumplimiento', {}).get('fecha_inicio_requerida'),
            'fecha_fin': getattr(otrosi, 'nuevo_fecha_fin_vigencia_cumplimiento', None) or valores_base.get('Cumplimiento', {}).get('fecha_fin_requerida'),
            'fuente': 'otrosi',
            'detalles': {
                'remuneraciones': get_valor_default('nuevo_valor_remuneraciones_cumplimiento') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('remuneraciones', 0) or 0),
                'servicios_publicos': get_valor_default('nuevo_valor_servicios_publicos_cumplimiento') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('servicios_publicos', 0) or 0),
                'iva': get_valor_default('nuevo_valor_iva_cumplimiento') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('iva', 0) or 0),
                'cuota_admon': get_valor_default('nuevo_valor_otros_cumplimiento') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('cuota_admon', 0) or 0),
                'cumplimiento_contrato': get_valor_default('nuevo_cumplimiento_amparo_cumplimiento_contrato') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('cumplimiento_contrato', 0) or 0),
                'buen_manejo_anticipo': get_valor_default('nuevo_cumplimiento_amparo_buen_manejo_anticipo') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('buen_manejo_anticipo', 0) or 0),
                'amortizacion_anticipo': get_valor_default('nuevo_cumplimiento_amparo_amortizacion_anticipo') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('amortizacion_anticipo', 0) or 0),
                'salarios_prestaciones': get_valor_default('nuevo_cumplimiento_amparo_salarios_prestaciones') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('salarios_prestaciones', 0) or 0),
                'aportes_seguridad_social': get_valor_default('nuevo_cumplimiento_amparo_aportes_seguridad_social') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('aportes_seguridad_social', 0) or 0),
                'calidad_servicio': get_valor_default('nuevo_cumplimiento_amparo_calidad_servicio') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('calidad_servicio', 0) or 0),
                'estabilidad_obra': get_valor_default('nuevo_cumplimiento_amparo_estabilidad_obra') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('estabilidad_obra', 0) or 0),
                'calidad_bienes': get_valor_default('nuevo_cumplimiento_amparo_calidad_bienes') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('calidad_bienes', 0) or 0),
                'multas': get_valor_default('nuevo_cumplimiento_amparo_multas') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('multas', 0) or 0),
                'clausula_penal': get_valor_default('nuevo_cumplimiento_amparo_clausula_penal') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('clausula_penal', 0) or 0),
                'sanciones_incumplimiento': get_valor_default('nuevo_cumplimiento_amparo_sanciones_incumplimiento') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('sanciones_incumplimiento', 0) or 0),
            }
        },
        'arrendamiento': {
            'exigida': getattr(otrosi, 'nuevo_exige_poliza_arrendamiento', None) if getattr(otrosi, 'nuevo_exige_poliza_arrendamiento', None) is not None else (valores_base.get('Poliza de Arrendamiento', {}).get('valor_requerido') is not None),
            'valor': get_valor('nuevo_valor_asegurado_arrendamiento') or (float(valores_base.get('Poliza de Arrendamiento', {}).get('valor_requerido', 0)) if valores_base.get('Poliza de Arrendamiento', {}).get('valor_requerido') else None),
            'vigencia': getattr(otrosi, 'nuevo_meses_vigencia_arrendamiento', None) or valores_base.get('Poliza de Arrendamiento', {}).get('meses_vigencia'),
            'fecha_inicio': getattr(otrosi, 'nuevo_fecha_inicio_vigencia_arrendamiento', None) or valores_base.get('Poliza de Arrendamiento', {}).get('fecha_inicio_requerida'),
            'fecha_fin': getattr(otrosi, 'nuevo_fecha_fin_vigencia_arrendamiento', None) or valores_base.get('Poliza de Arrendamiento', {}).get('fecha_fin_requerida'),
            'fuente': 'otrosi',
            'detalles': {
                'remuneraciones': get_valor_default('nuevo_valor_remuneraciones_arrendamiento') or (valores_base.get('Poliza de Arrendamiento', {}).get('detalles', {}).get('remuneraciones', 0) or 0),
                'servicios_publicos': get_valor_default('nuevo_valor_servicios_publicos_arrendamiento') or (valores_base.get('Poliza de Arrendamiento', {}).get('detalles', {}).get('servicios_publicos', 0) or 0),
                'iva': get_valor_default('nuevo_valor_iva_arrendamiento') or (valores_base.get('Poliza de Arrendamiento', {}).get('detalles', {}).get('iva', 0) or 0),
                'cuota_admon': get_valor_default('nuevo_valor_otros_arrendamiento') or (valores_base.get('Poliza de Arrendamiento', {}).get('detalles', {}).get('cuota_admon', 0) or 0),
            }
        },
        'todo_riesgo': {
            'exigida': getattr(otrosi, 'nuevo_exige_poliza_todo_riesgo', None) if getattr(otrosi, 'nuevo_exige_poliza_todo_riesgo', None) is not None else (valores_base.get('Arrendamiento', {}).get('valor_requerido') is not None),
            'valor': get_valor('nuevo_valor_asegurado_todo_riesgo') or (float(valores_base.get('Arrendamiento', {}).get('valor_requerido', 0)) if valores_base.get('Arrendamiento', {}).get('valor_requerido') else None),
            'vigencia': getattr(otrosi, 'nuevo_meses_vigencia_todo_riesgo', None) or valores_base.get('Arrendamiento', {}).get('meses_vigencia'),
            'fecha_inicio': getattr(otrosi, 'nuevo_fecha_inicio_vigencia_todo_riesgo', None) or valores_base.get('Arrendamiento', {}).get('fecha_inicio_requerida'),
            'fecha_fin': getattr(otrosi, 'nuevo_fecha_fin_vigencia_todo_riesgo', None) or valores_base.get('Arrendamiento', {}).get('fecha_fin_requerida'),
            'fuente': 'otrosi',
            'detalles': {}
        },
        'otra': {
            'exigida': getattr(otrosi, 'nuevo_exige_poliza_otra_1', None) if getattr(otrosi, 'nuevo_exige_poliza_otra_1', None) is not None else (valores_base.get('Otra', {}).get('valor_requerido') is not None),
            'nombre': getattr(otrosi, 'nuevo_nombre_poliza_otra_1', None) or valores_base.get('Otra', {}).get('nombre'),
            'valor': get_valor('nuevo_valor_asegurado_otra_1') or (float(valores_base.get('Otra', {}).get('valor_requerido', 0)) if valores_base.get('Otra', {}).get('valor_requerido') else None),
            'vigencia': getattr(otrosi, 'nuevo_meses_vigencia_otra_1', None) or valores_base.get('Otra', {}).get('meses_vigencia'),
            'fecha_inicio': getattr(otrosi, 'nuevo_fecha_inicio_vigencia_otra_1', None) or valores_base.get('Otra', {}).get('fecha_inicio_requerida'),
            'fecha_fin': getattr(otrosi, 'nuevo_fecha_fin_vigencia_otra_1', None) or valores_base.get('Otra', {}).get('fecha_fin_requerida'),
            'fuente': 'otrosi',
            'detalles': {}
        }
    }
    
    return requisitos


def _construir_requisitos_poliza_desde_renovacion(contrato, renovacion):
    """
    Construye los requisitos de pólizas usando los valores de la Renovación Automática específica.
    Similar a _construir_requisitos_poliza_desde_otrosi pero para RenovacionAutomatica.
    
    Args:
        contrato: Instancia del modelo Contrato
        renovacion: Instancia del modelo RenovacionAutomatica
    
    Returns:
        Diccionario con los requisitos de pólizas de la Renovación
    """
    # La estructura de RenovacionAutomatica es similar a OtroSi
    # Reutilizar la lógica pero adaptada para RenovacionAutomatica
    from datetime import timedelta
    from gestion.utils_otrosi import get_polizas_requeridas_contrato
    
    # Obtener valores base usando efecto cadena hasta antes de la Renovación
    fecha_antes_renovacion = renovacion.effective_from - timedelta(days=1) if renovacion.effective_from else date.today()
    valores_base = get_polizas_requeridas_contrato(contrato, fecha_antes_renovacion, permitir_fuera_vigencia=True)
    
    # Función auxiliar para obtener valor o None
    def get_valor(campo):
        valor = getattr(renovacion, campo, None)
        return float(valor) if valor else None
    
    # Función auxiliar para obtener valor o 0
    def get_valor_default(campo, default=0):
        valor = getattr(renovacion, campo, None)
        return float(valor) if valor else default
    
    # La estructura es idéntica a OtroSi, así que reutilizamos la misma lógica
    # pero adaptada para RenovacionAutomatica (tiene los mismos campos nuevo_*)
    requisitos = {
        'rce': {
            'exigida': getattr(renovacion, 'nuevo_exige_poliza_rce', None) if getattr(renovacion, 'nuevo_exige_poliza_rce', None) is not None else (valores_base.get('RCE - Responsabilidad Civil', {}).get('valor_requerido') is not None),
            'valor': get_valor('nuevo_valor_asegurado_rce') or (float(valores_base.get('RCE - Responsabilidad Civil', {}).get('valor_requerido', 0)) if valores_base.get('RCE - Responsabilidad Civil', {}).get('valor_requerido') else None),
            'vigencia': getattr(renovacion, 'nuevo_meses_vigencia_rce', None) or valores_base.get('RCE - Responsabilidad Civil', {}).get('meses_vigencia'),
            'fecha_inicio': getattr(renovacion, 'nuevo_fecha_inicio_vigencia_rce', None) or valores_base.get('RCE - Responsabilidad Civil', {}).get('fecha_inicio_requerida'),
            'fecha_fin': getattr(renovacion, 'nuevo_fecha_fin_vigencia_rce', None) or valores_base.get('RCE - Responsabilidad Civil', {}).get('fecha_fin_requerida'),
            'fuente': 'renovacion',
            'detalles': {
                'plo': get_valor_default('nuevo_valor_propietario_locatario_ocupante_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('plo', 0) or 0),
                'patronal': get_valor_default('nuevo_valor_patronal_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('patronal', 0) or 0),
                'gastos_medicos': get_valor_default('nuevo_valor_gastos_medicos_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('gastos_medicos', 0) or 0),
                'vehiculos': get_valor_default('nuevo_valor_vehiculos_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('vehiculos', 0) or 0),
                'contratistas': get_valor_default('nuevo_valor_contratistas_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('contratistas', 0) or 0),
                'perjuicios': get_valor_default('nuevo_valor_perjuicios_extrapatrimoniales_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('perjuicios', 0) or 0),
                'dano_moral': get_valor_default('nuevo_valor_dano_moral_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('dano_moral', 0) or 0),
                'lucro_cesante': get_valor_default('nuevo_valor_lucro_cesante_rce') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('lucro_cesante', 0) or 0),
                'danos_materiales': get_valor_default('nuevo_rce_cobertura_danos_materiales') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('danos_materiales', 0) or 0),
                'lesiones_personales': get_valor_default('nuevo_rce_cobertura_lesiones_personales') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('lesiones_personales', 0) or 0),
                'muerte_terceros': get_valor_default('nuevo_rce_cobertura_muerte_terceros') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('muerte_terceros', 0) or 0),
                'danos_bienes_terceros': get_valor_default('nuevo_rce_cobertura_danos_bienes_terceros') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('danos_bienes_terceros', 0) or 0),
                'responsabilidad_patronal': get_valor_default('nuevo_rce_cobertura_responsabilidad_patronal') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('responsabilidad_patronal', 0) or 0),
                'responsabilidad_cruzada': get_valor_default('nuevo_rce_cobertura_responsabilidad_cruzada') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('responsabilidad_cruzada', 0) or 0),
                'danos_contratistas': get_valor_default('nuevo_rce_cobertura_danos_contratistas') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('danos_contratistas', 0) or 0),
                'danos_ejecucion_contrato': get_valor_default('nuevo_rce_cobertura_danos_ejecucion_contrato') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('danos_ejecucion_contrato', 0) or 0),
                'danos_predios_vecinos': get_valor_default('nuevo_rce_cobertura_danos_predios_vecinos') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('danos_predios_vecinos', 0) or 0),
                'gastos_medicos_cobertura': get_valor_default('nuevo_rce_cobertura_gastos_medicos') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('gastos_medicos_cobertura', 0) or 0),
                'gastos_defensa': get_valor_default('nuevo_rce_cobertura_gastos_defensa') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('gastos_defensa', 0) or 0),
                'perjuicios_patrimoniales': get_valor_default('nuevo_rce_cobertura_perjuicios_patrimoniales') or (valores_base.get('RCE - Responsabilidad Civil', {}).get('detalles', {}).get('perjuicios_patrimoniales', 0) or 0),
            }
        },
        'cumplimiento': {
            'exigida': getattr(renovacion, 'nuevo_exige_poliza_cumplimiento', None) if getattr(renovacion, 'nuevo_exige_poliza_cumplimiento', None) is not None else (valores_base.get('Cumplimiento', {}).get('valor_requerido') is not None),
            'valor': get_valor('nuevo_valor_asegurado_cumplimiento') or (float(valores_base.get('Cumplimiento', {}).get('valor_requerido', 0)) if valores_base.get('Cumplimiento', {}).get('valor_requerido') else None),
            'vigencia': getattr(renovacion, 'nuevo_meses_vigencia_cumplimiento', None) or valores_base.get('Cumplimiento', {}).get('meses_vigencia'),
            'fecha_inicio': getattr(renovacion, 'nuevo_fecha_inicio_vigencia_cumplimiento', None) or valores_base.get('Cumplimiento', {}).get('fecha_inicio_requerida'),
            'fecha_fin': getattr(renovacion, 'nuevo_fecha_fin_vigencia_cumplimiento', None) or valores_base.get('Cumplimiento', {}).get('fecha_fin_requerida'),
            'fuente': 'renovacion',
            'detalles': {
                'remuneraciones': get_valor_default('nuevo_valor_remuneraciones_cumplimiento') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('remuneraciones', 0) or 0),
                'servicios_publicos': get_valor_default('nuevo_valor_servicios_publicos_cumplimiento') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('servicios_publicos', 0) or 0),
                'iva': get_valor_default('nuevo_valor_iva_cumplimiento') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('iva', 0) or 0),
                'cuota_admon': get_valor_default('nuevo_valor_otros_cumplimiento') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('cuota_admon', 0) or 0),
                'cumplimiento_contrato': get_valor_default('nuevo_cumplimiento_amparo_cumplimiento_contrato') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('cumplimiento_contrato', 0) or 0),
                'buen_manejo_anticipo': get_valor_default('nuevo_cumplimiento_amparo_buen_manejo_anticipo') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('buen_manejo_anticipo', 0) or 0),
                'amortizacion_anticipo': get_valor_default('nuevo_cumplimiento_amparo_amortizacion_anticipo') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('amortizacion_anticipo', 0) or 0),
                'salarios_prestaciones': get_valor_default('nuevo_cumplimiento_amparo_salarios_prestaciones') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('salarios_prestaciones', 0) or 0),
                'aportes_seguridad_social': get_valor_default('nuevo_cumplimiento_amparo_aportes_seguridad_social') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('aportes_seguridad_social', 0) or 0),
                'calidad_servicio': get_valor_default('nuevo_cumplimiento_amparo_calidad_servicio') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('calidad_servicio', 0) or 0),
                'estabilidad_obra': get_valor_default('nuevo_cumplimiento_amparo_estabilidad_obra') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('estabilidad_obra', 0) or 0),
                'calidad_bienes': get_valor_default('nuevo_cumplimiento_amparo_calidad_bienes') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('calidad_bienes', 0) or 0),
                'multas': get_valor_default('nuevo_cumplimiento_amparo_multas') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('multas', 0) or 0),
                'clausula_penal': get_valor_default('nuevo_cumplimiento_amparo_clausula_penal') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('clausula_penal', 0) or 0),
                'sanciones_incumplimiento': get_valor_default('nuevo_cumplimiento_amparo_sanciones_incumplimiento') or (valores_base.get('Cumplimiento', {}).get('detalles', {}).get('sanciones_incumplimiento', 0) or 0),
            }
        },
        'arrendamiento': {
            'exigida': getattr(renovacion, 'nuevo_exige_poliza_arrendamiento', None) if getattr(renovacion, 'nuevo_exige_poliza_arrendamiento', None) is not None else (valores_base.get('Poliza de Arrendamiento', {}).get('valor_requerido') is not None),
            'valor': get_valor('nuevo_valor_asegurado_arrendamiento') or (float(valores_base.get('Poliza de Arrendamiento', {}).get('valor_requerido', 0)) if valores_base.get('Poliza de Arrendamiento', {}).get('valor_requerido') else None),
            'vigencia': getattr(renovacion, 'nuevo_meses_vigencia_arrendamiento', None) or valores_base.get('Poliza de Arrendamiento', {}).get('meses_vigencia'),
            'fecha_inicio': getattr(renovacion, 'nuevo_fecha_inicio_vigencia_arrendamiento', None) or valores_base.get('Poliza de Arrendamiento', {}).get('fecha_inicio_requerida'),
            'fecha_fin': getattr(renovacion, 'nuevo_fecha_fin_vigencia_arrendamiento', None) or valores_base.get('Poliza de Arrendamiento', {}).get('fecha_fin_requerida'),
            'fuente': 'renovacion',
            'detalles': {
                'remuneraciones': get_valor_default('nuevo_valor_remuneraciones_arrendamiento') or (valores_base.get('Poliza de Arrendamiento', {}).get('detalles', {}).get('remuneraciones', 0) or 0),
                'servicios_publicos': get_valor_default('nuevo_valor_servicios_publicos_arrendamiento') or (valores_base.get('Poliza de Arrendamiento', {}).get('detalles', {}).get('servicios_publicos', 0) or 0),
                'iva': get_valor_default('nuevo_valor_iva_arrendamiento') or (valores_base.get('Poliza de Arrendamiento', {}).get('detalles', {}).get('iva', 0) or 0),
                'cuota_admon': get_valor_default('nuevo_valor_otros_arrendamiento') or (valores_base.get('Poliza de Arrendamiento', {}).get('detalles', {}).get('cuota_admon', 0) or 0),
            }
        },
        'todo_riesgo': {
            'exigida': getattr(renovacion, 'nuevo_exige_poliza_todo_riesgo', None) if getattr(renovacion, 'nuevo_exige_poliza_todo_riesgo', None) is not None else (valores_base.get('Arrendamiento', {}).get('valor_requerido') is not None),
            'valor': get_valor('nuevo_valor_asegurado_todo_riesgo') or (float(valores_base.get('Arrendamiento', {}).get('valor_requerido', 0)) if valores_base.get('Arrendamiento', {}).get('valor_requerido') else None),
            'vigencia': getattr(renovacion, 'nuevo_meses_vigencia_todo_riesgo', None) or valores_base.get('Arrendamiento', {}).get('meses_vigencia'),
            'fecha_inicio': getattr(renovacion, 'nuevo_fecha_inicio_vigencia_todo_riesgo', None) or valores_base.get('Arrendamiento', {}).get('fecha_inicio_requerida'),
            'fecha_fin': getattr(renovacion, 'nuevo_fecha_fin_vigencia_todo_riesgo', None) or valores_base.get('Arrendamiento', {}).get('fecha_fin_requerida'),
            'fuente': 'renovacion',
            'detalles': {}
        },
        'otra': {
            'exigida': getattr(renovacion, 'nuevo_exige_poliza_otra_1', None) if getattr(renovacion, 'nuevo_exige_poliza_otra_1', None) is not None else (valores_base.get('Otra', {}).get('valor_requerido') is not None),
            'nombre': getattr(renovacion, 'nuevo_nombre_poliza_otra_1', None) or valores_base.get('Otra', {}).get('nombre'),
            'valor': get_valor('nuevo_valor_asegurado_otra_1') or (float(valores_base.get('Otra', {}).get('valor_requerido', 0)) if valores_base.get('Otra', {}).get('valor_requerido') else None),
            'vigencia': getattr(renovacion, 'nuevo_meses_vigencia_otra_1', None) or valores_base.get('Otra', {}).get('meses_vigencia'),
            'fecha_inicio': getattr(renovacion, 'nuevo_fecha_inicio_vigencia_otra_1', None) or valores_base.get('Otra', {}).get('fecha_inicio_requerida'),
            'fecha_fin': getattr(renovacion, 'nuevo_fecha_fin_vigencia_otra_1', None) or valores_base.get('Otra', {}).get('fecha_fin_requerida'),
            'fuente': 'renovacion',
            'detalles': {}
        }
    }
    
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


def _estado_vigente_contrato(contrato, fecha_actual=None):
    """
    Determina si el contrato está vigente en la fecha dada.
    Misma lógica que lista_contratos para mantener consistencia dashboard/lista.
    """
    from gestion.utils_otrosi import get_otrosi_vigente

    if fecha_actual is None:
        fecha_actual = date.today()

    otrosi_vigente_actual = get_otrosi_vigente(contrato, fecha_actual)
    fecha_final_vigente = _obtener_fecha_final_contrato(contrato, fecha_actual)

    if otrosi_vigente_actual:
        if otrosi_vigente_actual.effective_to:
            return otrosi_vigente_actual.effective_from <= fecha_actual <= otrosi_vigente_actual.effective_to
        if otrosi_vigente_actual.nueva_fecha_final_actualizada:
            return otrosi_vigente_actual.nueva_fecha_final_actualizada >= fecha_actual
        return otrosi_vigente_actual.effective_from <= fecha_actual
    if contrato.vigente:
        if fecha_final_vigente:
            return fecha_final_vigente >= fecha_actual
        return True
    return False


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

