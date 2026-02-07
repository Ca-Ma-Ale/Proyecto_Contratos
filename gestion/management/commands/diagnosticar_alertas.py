"""
Comando para diagnosticar problemas con las alertas.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
import logging

from gestion.models import ConfiguracionAlerta
from gestion.services.alerta_email_service import AlertaEmailService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Diagnostica problemas con las alertas por tipo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tipo',
            type=str,
            help='Tipo específico de alerta a diagnosticar',
            choices=[
                'VENCIMIENTO_CONTRATOS',
                'ALERTAS_IPC',
                'ALERTAS_SALARIO_MINIMO',
                'POLIZAS_CRITICAS',
                'PREAVISO_RENOVACION',
                'POLIZAS_REQUERIDAS',
                'TERMINACION_ANTICIPADA',
                'RENOVACION_AUTOMATICA',
            ]
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Diagnóstico de Alertas ===\n'))
        
        tipo_especifico = options.get('tipo')
        servicio = AlertaEmailService()
        fecha_ref = timezone.now().date()
        
        if tipo_especifico:
            tipos_a_diagnosticar = [tipo_especifico]
        else:
            tipos_a_diagnosticar = [
                'VENCIMIENTO_CONTRATOS',
                'ALERTAS_IPC',
                'ALERTAS_SALARIO_MINIMO',
                'POLIZAS_CRITICAS',
                'PREAVISO_RENOVACION',
                'POLIZAS_REQUERIDAS',
                'TERMINACION_ANTICIPADA',
                'RENOVACION_AUTOMATICA',
            ]
        
        for tipo_alerta in tipos_a_diagnosticar:
            self.stdout.write(f'\n--- {tipo_alerta} ---')
            
            try:
                config = ConfiguracionAlerta.objects.get(tipo_alerta=tipo_alerta)
                self.stdout.write(f'  Configuración encontrada: ✓')
                self.stdout.write(f'  Activa: {"Sí" if config.activo else "No"}')
                self.stdout.write(f'  Solo críticas: {"Sí" if config.solo_criticas else "No"}')
                self.stdout.write(f'  Frecuencia: {config.get_frecuencia_display()}')
                self.stdout.write(f'  Hora de envío: {config.hora_envio}')
                
                destinatarios = servicio.obtener_destinatarios(tipo_alerta)
                self.stdout.write(f'  Destinatarios: {len(destinatarios)}')
                if destinatarios:
                    for dest in destinatarios:
                        self.stdout.write(f'    - {dest.email} ({dest.nombre or "Sin nombre"})')
                else:
                    self.stdout.write(self.style.WARNING('    ⚠ No hay destinatarios configurados'))
                
                alertas_sin_filtro = servicio.obtener_alertas_por_tipo(
                    tipo_alerta=tipo_alerta,
                    fecha_referencia=fecha_ref,
                    solo_criticas=False
                )
                self.stdout.write(f'  Alertas sin filtro: {len(alertas_sin_filtro)}')
                
                if config.solo_criticas:
                    alertas_con_filtro = servicio.obtener_alertas_por_tipo(
                        tipo_alerta=tipo_alerta,
                        fecha_referencia=fecha_ref,
                        solo_criticas=True
                    )
                    self.stdout.write(f'  Alertas con filtro "solo críticas": {len(alertas_con_filtro)}')
                    
                    if len(alertas_sin_filtro) > 0 and len(alertas_con_filtro) == 0:
                        self.stdout.write(self.style.WARNING(
                            f'    ⚠ PROBLEMA: Hay {len(alertas_sin_filtro)} alerta(s) pero ninguna es crítica (danger)'
                        ))
                        colores = {}
                        for alerta in alertas_sin_filtro:
                            color = getattr(alerta, 'color_alerta', 'unknown')
                            colores[color] = colores.get(color, 0) + 1
                        self.stdout.write(f'    Distribución de colores: {colores}')
                
                debe_enviar = config.debe_enviar_hoy(fecha_ref)
                self.stdout.write(f'  Debe enviar hoy: {"Sí" if debe_enviar else "No"}')
                
            except ConfiguracionAlerta.DoesNotExist:
                self.stdout.write(self.style.ERROR('  ✗ Configuración no encontrada'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                logger.error(f"Error al diagnosticar {tipo_alerta}: {str(e)}", exc_info=True)
        
        self.stdout.write('\n' + '='*60)
