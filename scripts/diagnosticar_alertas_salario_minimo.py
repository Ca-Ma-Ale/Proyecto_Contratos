#!/usr/bin/env python
"""
Script para diagnosticar problemas con alertas de salario mínimo.
Ejecutar desde el directorio del proyecto: python scripts/diagnosticar_alertas_salario_minimo.py
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratos.settings')
django.setup()

from django.utils import timezone
from gestion.models import ConfiguracionAlerta
from gestion.services.alerta_email_service import AlertaEmailService

def diagnosticar_alertas_salario_minimo():
    print("=== Diagnóstico de Alertas de Salario Mínimo ===\n")
    
    servicio = AlertaEmailService()
    fecha_ref = timezone.now().date()
    tipo_alerta = 'ALERTAS_SALARIO_MINIMO'
    
    print(f'--- {tipo_alerta} ---')
    
    try:
        config = ConfiguracionAlerta.objects.get(tipo_alerta=tipo_alerta)
        print(f'✓ Configuración encontrada')
        print(f'  Activa: {"Sí" if config.activo else "No"}')
        print(f'  Solo críticas: {"Sí" if config.solo_criticas else "No"}')
        print(f'  Frecuencia: {config.get_frecuencia_display()}')
        print(f'  Hora de envío: {config.hora_envio}')
        print(f'  Días de semana: {config.dias_semana}')
        
        destinatarios = servicio.obtener_destinatarios(tipo_alerta)
        print(f'\n  Destinatarios: {len(destinatarios)}')
        if destinatarios:
            for dest in destinatarios:
                print(f'    - {dest.email} ({dest.nombre or "Sin nombre"})')
        else:
            print('    ⚠ No hay destinatarios configurados')
        
        print(f'\n  Obteniendo alertas sin filtro...')
        alertas_sin_filtro = servicio.obtener_alertas_por_tipo(
            tipo_alerta=tipo_alerta,
            fecha_referencia=fecha_ref,
            solo_criticas=False
        )
        print(f'  Alertas sin filtro: {len(alertas_sin_filtro)}')
        
        if alertas_sin_filtro:
            colores = {}
            for alerta in alertas_sin_filtro:
                color = getattr(alerta, 'color_alerta', 'unknown')
                colores[color] = colores.get(color, 0) + 1
            print(f'  Distribución de colores: {colores}')
        
        if config.solo_criticas:
            print(f'\n  Obteniendo alertas con filtro "solo críticas"...')
            alertas_con_filtro = servicio.obtener_alertas_por_tipo(
                tipo_alerta=tipo_alerta,
                fecha_referencia=fecha_ref,
                solo_criticas=True
            )
            print(f'  Alertas con filtro "solo críticas": {len(alertas_con_filtro)}')
            
            if len(alertas_sin_filtro) > 0 and len(alertas_con_filtro) == 0:
                print(f'\n  ⚠ PROBLEMA DETECTADO:')
                print(f'     Hay {len(alertas_sin_filtro)} alerta(s) pero ninguna es crítica (danger)')
                print(f'     El filtro "solo críticas" está eliminando todas las alertas')
                print(f'     SOLUCIÓN: Desactivar "Solo Alertas Críticas" en la configuración')
        
        debe_enviar = config.debe_enviar_hoy(fecha_ref)
        print(f'\n  Debe enviar hoy ({fecha_ref}): {"Sí" if debe_enviar else "No"}')
        
        if not debe_enviar:
            print(f'  ⚠ No es el día programado para enviar esta alerta')
            print(f'     Frecuencia: {config.get_frecuencia_display()}')
            if config.frecuencia == 'SEMANAL':
                dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                dias_config = [dias_nombres[d] for d in config.dias_semana]
                print(f'     Días configurados: {", ".join(dias_config)}')
                dia_actual = fecha_ref.weekday()
                print(f'     Día actual: {dias_nombres[dia_actual]}')
        
    except ConfiguracionAlerta.DoesNotExist:
        print('  ✗ Configuración no encontrada')
    except Exception as e:
        print(f'  ✗ Error: {str(e)}')
        import traceback
        traceback.print_exc()
    
    print('\n' + '='*60)

if __name__ == '__main__':
    diagnosticar_alertas_salario_minimo()
