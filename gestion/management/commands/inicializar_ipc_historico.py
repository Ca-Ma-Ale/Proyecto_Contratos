"""
Comando de gestión para inicializar el histórico de IPC con los datos proporcionados.
Ejecutar con: python manage.py inicializar_ipc_historico
"""
from django.core.management.base import BaseCommand
from gestion.models import IPCHistorico
from decimal import Decimal


class Command(BaseCommand):
    help = 'Inicializa el histórico de IPC con los valores históricos del DANE'

    def handle(self, *args, **options):
        self.stdout.write('Inicializando histórico de IPC...')
        
        datos_ipc = {
            2010: Decimal('3.17'),
            2011: Decimal('3.73'),
            2012: Decimal('2.44'),
            2013: Decimal('1.94'),
            2014: Decimal('3.66'),
            2015: Decimal('6.77'),
            2016: Decimal('5.75'),
            2017: Decimal('4.09'),
            2018: Decimal('3.18'),
            2019: Decimal('3.80'),
            2020: Decimal('1.61'),
            2021: Decimal('5.62'),
            2022: Decimal('13.12'),
            2023: Decimal('9.28'),
            2024: Decimal('5.20'),
        }
        
        creados = 0
        actualizados = 0
        
        for año, valor in datos_ipc.items():
            ipc, created = IPCHistorico.objects.get_or_create(
                año=año,
                defaults={
                    'valor_ipc': valor,
                    'creado_por': 'Sistema - Inicialización',
                }
            )
            
            if not created:
                ipc.valor_ipc = valor
                ipc.modificado_por = 'Sistema - Inicialización'
                ipc.save()
                actualizados += 1
                self.stdout.write(self.style.WARNING(f'  IPC {año} actualizado: {valor}%'))
            else:
                creados += 1
                self.stdout.write(self.style.SUCCESS(f'  IPC {año} creado: {valor}%'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\nInicialización completada! Creados: {creados}, Actualizados: {actualizados}'
        ))

