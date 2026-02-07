#!/usr/bin/env python
"""
Script detallado para diagnosticar por qué no se encuentran alertas de salario mínimo.
Ejecutar desde el directorio del proyecto: python scripts/diagnosticar_salario_minimo_detallado.py
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratos.settings')
django.setup()

from django.utils import timezone
from gestion.models import Contrato, CalculoSalarioMinimo
from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo_hasta_fecha
from gestion.utils_ipc import calcular_proxima_fecha_aumento

def diagnosticar_detallado():
    print("=== Diagnóstico Detallado de Alertas de Salario Mínimo ===\n")
    
    fecha_base = timezone.now().date()
    print(f"Fecha de referencia: {fecha_base}\n")
    
    # Paso 1: Contratos vigentes
    contratos_vigentes = Contrato.objects.filter(vigente=True).count()
    print(f"1. Contratos vigentes: {contratos_vigentes}")
    
    contratos_con_sm = Contrato.objects.filter(vigente=True)
    print(f"   Analizando {contratos_con_sm.count()} contratos vigentes...\n")
    
    estadisticas = {
        'total_contratos': 0,
        'con_tipo_sm': 0,
        'con_periodicidad_anual': 0,
        'con_fecha_calculable': 0,
        'sin_calculo_existente': 0,
        'dentro_ventana_90_dias': 0,
        'alertas_finales': 0,
    }
    
    contratos_procesados = 0
    contratos_con_problemas = []
    
    for contrato in contratos_con_sm[:50]:  # Limitar a 50 para no saturar
        estadisticas['total_contratos'] += 1
        problemas = []
        
        # Obtener valores actualizados
        otrosi_tipo_ipc = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nuevo_tipo_condicion_ipc', fecha_base
        )
        otrosi_periodicidad = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_periodicidad_ipc', fecha_base
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
        
        # Verificar tipo SALARIO_MINIMO
        if not tipo_condicion_ipc or tipo_condicion_ipc != 'SALARIO_MINIMO':
            continue
        
        estadisticas['con_tipo_sm'] += 1
        
        # Verificar periodicidad ANUAL
        if periodicidad_ipc not in ['ANUAL']:
            problemas.append(f"Periodicidad: {periodicidad_ipc} (requiere ANUAL)")
            continue
        
        estadisticas['con_periodicidad_anual'] += 1
        
        # Calcular fecha de aumento
        fecha_aumento_anual = calcular_proxima_fecha_aumento(contrato, fecha_base)
        if not fecha_aumento_anual:
            problemas.append("No se pudo calcular fecha_aumento_anual")
            continue
        
        estadisticas['con_fecha_calculable'] += 1
        
        # Verificar si ya existe cálculo
        calculo_existente = CalculoSalarioMinimo.objects.filter(
            contrato=contrato,
            fecha_aplicacion=fecha_aumento_anual
        ).exists()
        
        if calculo_existente:
            problemas.append(f"Ya existe cálculo para fecha {fecha_aumento_anual}")
            continue
        
        estadisticas['sin_calculo_existente'] += 1
        
        # Calcular días restantes
        dias_restantes = (fecha_aumento_anual - fecha_base).days
        
        if dias_restantes > 90:
            problemas.append(f"Días restantes: {dias_restantes} (requiere <= 90)")
            continue
        
        estadisticas['dentro_ventana_90_dias'] += 1
        estadisticas['alertas_finales'] += 1
        
        if problemas:
            contratos_con_problemas.append({
                'contrato': contrato.num_contrato,
                'problemas': problemas
            })
    
    print("\n=== Estadísticas de Filtrado ===")
    print(f"Total contratos analizados: {estadisticas['total_contratos']}")
    print(f"  ✓ Con tipo SALARIO_MINIMO: {estadisticas['con_tipo_sm']}")
    print(f"  ✓ Con periodicidad ANUAL: {estadisticas['con_periodicidad_anual']}")
    print(f"  ✓ Con fecha calculable: {estadisticas['con_fecha_calculable']}")
    print(f"  ✓ Sin cálculo existente: {estadisticas['sin_calculo_existente']}")
    print(f"  ✓ Dentro de ventana 90 días: {estadisticas['dentro_ventana_90_dias']}")
    print(f"  ✓ Alertas finales: {estadisticas['alertas_finales']}")
    
    if estadisticas['alertas_finales'] == 0:
        print("\n⚠ PROBLEMA: No se encontraron alertas después de aplicar todos los filtros")
        print("\nPosibles causas:")
        if estadisticas['con_tipo_sm'] == 0:
            print("  - No hay contratos con tipo_condicion_ipc = 'SALARIO_MINIMO'")
        elif estadisticas['con_periodicidad_anual'] == 0:
            print("  - Los contratos con SALARIO_MINIMO no tienen periodicidad ANUAL")
        elif estadisticas['con_fecha_calculable'] < estadisticas['con_periodicidad_anual']:
            print("  - Algunos contratos no pueden calcular fecha_aumento_anual")
        elif estadisticas['sin_calculo_existente'] < estadisticas['con_fecha_calculable']:
            print("  - Muchos contratos ya tienen cálculos existentes para las fechas")
        elif estadisticas['dentro_ventana_90_dias'] < estadisticas['sin_calculo_existente']:
            print("  - Las fechas de ajuste están a más de 90 días")
    
    if contratos_con_problemas:
        print(f"\n=== Contratos con problemas (primeros 10) ===")
        for item in contratos_con_problemas[:10]:
            print(f"  Contrato {item['contrato']}: {', '.join(item['problemas'])}")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    diagnosticar_detallado()
