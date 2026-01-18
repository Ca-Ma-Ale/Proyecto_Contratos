"""
Comando de management para enviar alertas por correo electrónico.
Este comando debe ejecutarse periódicamente (ej: todos los lunes a las 8:00 AM)
usando cron o programador de tareas.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
import logging

from gestion.services.alerta_email_service import AlertaEmailService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Envía alertas por correo electrónico según la configuración programada'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tipo',
            type=str,
            help='Tipo específico de alerta a enviar (opcional)',
            choices=[
                'VENCIMIENTO_CONTRATOS',
                'ALERTAS_IPC',
                'POLIZAS_CRITICAS',
                'PREAVISO_RENOVACION',
                'POLIZAS_REQUERIDAS',
                'TERMINACION_ANTICIPADA',
                'RENOVACION_AUTOMATICA',
            ]
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Forzar envío aunque no sea el día programado',
        )
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha de referencia en formato YYYY-MM-DD (por defecto hoy)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando envío de alertas por correo...'))
        
        fecha_referencia = None
        if options['fecha']:
            try:
                fecha_referencia = date.fromisoformat(options['fecha'])
            except ValueError:
                self.stdout.write(self.style.ERROR(f'Fecha inválida: {options["fecha"]}'))
                return
        
        servicio = AlertaEmailService()
        
        tipo_especifico = options.get('tipo')
        forzar_envio = options.get('forzar', False)
        
        if tipo_especifico:
            self.stdout.write(f'Enviando alertas de tipo: {tipo_especifico}')
            resultado = servicio.enviar_alertas_tipo(
                tipo_alerta=tipo_especifico,
                fecha_referencia=fecha_referencia,
                forzar_envio=forzar_envio
            )
            self._mostrar_resultado(resultado)
        else:
            self.stdout.write('Enviando todas las alertas programadas...')
            resultados = servicio.enviar_todas_alertas_programadas(fecha_referencia=fecha_referencia)
            
            if not resultados:
                self.stdout.write(self.style.WARNING('No hay alertas programadas para hoy'))
                return
            
            self.stdout.write(f'\nProcesadas {len(resultados)} configuración(es) de alerta:\n')
            
            for resultado in resultados:
                self._mostrar_resultado(resultado)
            
            total_enviados = sum(1 for r in resultados if r['enviado'])
            total_errores = sum(len(r['errores']) for r in resultados)
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(f'Resumen: {total_enviados} tipo(s) enviado(s) exitosamente')
            if total_errores > 0:
                self.stdout.write(self.style.WARNING(f'{total_errores} error(es) encontrado(s)'))
            else:
                self.stdout.write(self.style.SUCCESS('Todos los envíos fueron exitosos'))
    
    def _mostrar_resultado(self, resultado):
        """Muestra el resultado de un envío de alertas"""
        tipo = resultado['tipo_alerta']
        nombre_tipo = dict(AlertaEmailService.MAPEO_NOMBRES_ALERTA).get(tipo, tipo)
        
        self.stdout.write(f'\n--- {nombre_tipo} ---')
        
        if resultado['enviado']:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Enviado a {resultado['destinatarios']} destinatario(s) "
                    f"({resultado['alertas_enviadas']} alerta(s))"
                )
            )
        else:
            self.stdout.write(self.style.WARNING('[ERROR] No se pudo enviar'))
        
        if resultado['errores']:
            for error in resultado['errores']:
                self.stdout.write(self.style.ERROR(f"  Error: {error}"))

