"""
Comando para configurar todas las alertas con valores por defecto.
Crea configuraciones para todos los tipos de alertas disponibles.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import time
from gestion.models import ConfiguracionAlerta, TIPO_ALERTA_CHOICES


class Command(BaseCommand):
    help = 'Configura todas las alertas con valores por defecto'

    def add_arguments(self, parser):
        parser.add_argument(
            '--frecuencia',
            type=str,
            default='SEMANAL',
            choices=['INMEDIATO', 'DIARIO', 'SEMANAL', 'MENSUAL'],
            help='Frecuencia de envío para todas las alertas (por defecto: SEMANAL)',
        )
        parser.add_argument(
            '--dias',
            type=str,
            default='0',
            help='Días de la semana para frecuencia semanal (separados por comas, 0=Lunes). Por defecto: 0 (Lunes)',
        )
        parser.add_argument(
            '--hora',
            type=str,
            default='08:00',
            help='Hora de envío en formato HH:MM (por defecto: 08:00)',
        )
        parser.add_argument(
            '--solo-criticas',
            action='store_true',
            help='Configurar solo alertas críticas para todas las alertas',
        )
        parser.add_argument(
            '--inactivas',
            action='store_true',
            help='Crear las alertas inactivas (por defecto se crean activas)',
        )
        parser.add_argument(
            '--sobrescribir',
            action='store_true',
            help='Sobrescribir configuraciones existentes',
        )

    def handle(self, *args, **options):
        frecuencia = options['frecuencia']
        dias_str = options['dias']
        hora_str = options['hora']
        solo_criticas = options['solo_criticas']
        activo = not options['inactivas']
        sobrescribir = options['sobrescribir']
        
        # Parsear días de la semana
        dias_semana = []
        if frecuencia == 'SEMANAL':
            try:
                dias_semana = [int(d.strip()) for d in dias_str.split(',')]
                # Validar que los días estén en rango 0-6
                dias_semana = [d for d in dias_semana if 0 <= d <= 6]
                if not dias_semana:
                    self.stdout.write(self.style.WARNING('Días inválidos, usando Lunes por defecto'))
                    dias_semana = [0]
            except ValueError:
                self.stdout.write(self.style.WARNING('Error al parsear días, usando Lunes por defecto'))
                dias_semana = [0]
        
        # Parsear hora
        try:
            hora_parts = hora_str.split(':')
            hora_envio = time(int(hora_parts[0]), int(hora_parts[1]))
        except (ValueError, IndexError):
            self.stdout.write(self.style.WARNING('Hora inválida, usando 08:00 por defecto'))
            hora_envio = time(8, 0)
        
        self.stdout.write(self.style.SUCCESS('Configurando alertas...'))
        self.stdout.write(f'Frecuencia: {frecuencia}')
        if frecuencia == 'SEMANAL':
            dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            dias_display = ', '.join([dias_nombres[d] for d in dias_semana])
            self.stdout.write(f'Días: {dias_display}')
        self.stdout.write(f'Hora: {hora_envio.strftime("%H:%M")}')
        self.stdout.write(f'Solo críticas: {"Sí" if solo_criticas else "No"}')
        self.stdout.write(f'Activas: {"Sí" if activo else "No"}')
        self.stdout.write('')
        
        creadas = 0
        actualizadas = 0
        existentes = 0
        
        for tipo_codigo, tipo_nombre in TIPO_ALERTA_CHOICES:
            try:
                config, created = ConfiguracionAlerta.objects.get_or_create(
                    tipo_alerta=tipo_codigo,
                    defaults={
                        'activo': activo,
                        'frecuencia': frecuencia,
                        'dias_semana': dias_semana,
                        'hora_envio': hora_envio,
                        'solo_criticas': solo_criticas,
                        'asunto': None,
                    }
                )
                
                if created:
                    creadas += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'[OK] Creada: {tipo_nombre}')
                    )
                else:
                    if sobrescribir:
                        config.activo = activo
                        config.frecuencia = frecuencia
                        config.dias_semana = dias_semana
                        config.hora_envio = hora_envio
                        config.solo_criticas = solo_criticas
                        config.save()
                        actualizadas += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'[ACTUALIZADA] {tipo_nombre}')
                        )
                    else:
                        existentes += 1
                        self.stdout.write(
                            self.style.WARNING(f'[EXISTE] {tipo_nombre} (usa --sobrescribir para actualizar)')
                        )
                        
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[ERROR] {tipo_nombre}: {str(e)}')
                )
        
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'Resumen:'))
        self.stdout.write(f'  Creadas: {creadas}')
        if sobrescribir:
            self.stdout.write(f'  Actualizadas: {actualizadas}')
        if existentes > 0:
            self.stdout.write(f'  Existentes (no modificadas): {existentes}')
        self.stdout.write('')
        self.stdout.write('Próximo paso: Configurar destinatarios en:')
        self.stdout.write('  /admin/gestion/destinatarioalerta/add/')

