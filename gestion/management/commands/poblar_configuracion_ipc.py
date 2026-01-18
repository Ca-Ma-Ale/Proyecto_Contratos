"""
Comando de gestión para poblar los datos iniciales de configuración IPC
desde las constantes hardcodeadas.
"""
from django.core.management.base import BaseCommand
from gestion.models import TipoCondicionIPC, PeriodicidadIPC


class Command(BaseCommand):
    help = 'Pobla los datos iniciales de tipos de condición IPC y periodicidades desde las constantes'

    def handle(self, *args, **options):
        self.stdout.write('Poblando configuración IPC inicial...')
        
        # Poblar tipos de condición IPC
        tipos_condicion = [
            {'codigo': 'IPC', 'nombre': 'IPC', 'descripcion': 'Índice de Precios al Consumidor', 'orden': 1},
            {'codigo': 'SALARIO_MINIMO', 'nombre': 'Porcentaje Salario Mínimo', 'descripcion': 'Ajuste basado en porcentaje del salario mínimo', 'orden': 2},
        ]
        
        for tipo_data in tipos_condicion:
            tipo, created = TipoCondicionIPC.objects.get_or_create(
                codigo=tipo_data['codigo'],
                defaults={
                    'nombre': tipo_data['nombre'],
                    'descripcion': tipo_data['descripcion'],
                    'orden': tipo_data['orden'],
                    'activo': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Tipo de condicion IPC "{tipo.nombre}" creado'))
            else:
                self.stdout.write(self.style.WARNING(f'  Tipo de condicion IPC "{tipo.nombre}" ya existe'))
        
        # Poblar periodicidades IPC
        periodicidades = [
            {'codigo': 'ANUAL', 'nombre': 'Anual', 'descripcion': 'Ajuste anual del IPC', 'orden': 1},
            {'codigo': 'FECHA_ESPECIFICA', 'nombre': 'Fecha Específica', 'descripcion': 'Ajuste en una fecha específica del año', 'orden': 2},
        ]
        
        for periodicidad_data in periodicidades:
            periodicidad, created = PeriodicidadIPC.objects.get_or_create(
                codigo=periodicidad_data['codigo'],
                defaults={
                    'nombre': periodicidad_data['nombre'],
                    'descripcion': periodicidad_data['descripcion'],
                    'orden': periodicidad_data['orden'],
                    'activo': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Periodicidad IPC "{periodicidad.nombre}" creada'))
            else:
                self.stdout.write(self.style.WARNING(f'  Periodicidad IPC "{periodicidad.nombre}" ya existe'))
        
        self.stdout.write(self.style.SUCCESS('\nConfiguracion IPC inicial completada!'))

