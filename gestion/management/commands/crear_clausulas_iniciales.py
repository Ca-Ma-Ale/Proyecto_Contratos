from django.core.management.base import BaseCommand
from gestion.models import Clausula


class Command(BaseCommand):
    help = 'Crea cláusulas genéricas iniciales para el sistema'

    def handle(self, *args, **options):
        clausulas_genericas = [
            {'titulo': 'Cláusula de Cumplimiento', 'orden': 1},
            {'titulo': 'Cláusula de Confidencialidad', 'orden': 2},
            {'titulo': 'Cláusula de Protección de Datos Personales', 'orden': 3},
            {'titulo': 'Cláusula SARLAFT', 'orden': 4},
            {'titulo': 'Cláusula de Terminación Anticipada', 'orden': 5},
            {'titulo': 'Cláusula de Penalización por Incumplimiento', 'orden': 6},
            {'titulo': 'Cláusula de Pólizas de Seguro', 'orden': 7},
            {'titulo': 'Cláusula de Renovación', 'orden': 8},
            {'titulo': 'Cláusula de Modificaciones', 'orden': 9},
            {'titulo': 'Cláusula de Solución de Controversias', 'orden': 10},
            {'titulo': 'Cláusula de Fuerza Mayor', 'orden': 11},
            {'titulo': 'Cláusula de Propiedad Intelectual', 'orden': 12},
            {'titulo': 'Cláusula de Subcontratación', 'orden': 13},
            {'titulo': 'Cláusula de Garantías', 'orden': 14},
            {'titulo': 'Cláusula de Facturación y Pagos', 'orden': 15},
        ]
        
        creadas = 0
        actualizadas = 0
        
        for clausula_data in clausulas_genericas:
            clausula, created = Clausula.objects.update_or_create(
                titulo=clausula_data['titulo'],
                defaults={
                    'orden': clausula_data['orden'],
                    'activa': True
                }
            )
            
            if created:
                creadas += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Clausula creada: {clausula.titulo}')
                )
            else:
                actualizadas += 1
                self.stdout.write(
                    self.style.WARNING(f'Clausula actualizada: {clausula.titulo}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nProceso completado: {creadas} clausulas creadas, {actualizadas} actualizadas.'
            )
        )
