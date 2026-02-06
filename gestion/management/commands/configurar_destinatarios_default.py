"""
Comando para configurar destinatarios para todas las alertas.
Agrega un email como destinatario a todos los tipos de alertas activas.
"""

from django.core.management.base import BaseCommand
from gestion.models import ConfiguracionAlerta, DestinatarioAlerta


class Command(BaseCommand):
    help = 'Configura destinatarios para todas las alertas activas'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email del destinatario a agregar',
        )
        parser.add_argument(
            '--nombre',
            type=str,
            default='',
            help='Nombre del destinatario (opcional)',
        )
        parser.add_argument(
            '--solo-activas',
            action='store_true',
            default=True,
            help='Agregar solo a alertas activas (por defecto: True)',
        )
        parser.add_argument(
            '--sobrescribir',
            action='store_true',
            help='Si el destinatario ya existe, actualizarlo',
        )

    def handle(self, *args, **options):
        email = options['email']
        nombre = options['nombre']
        solo_activas = options['solo_activas']
        sobrescribir = options['sobrescribir']
        
        if not email:
            self.stdout.write(self.style.ERROR('Debe proporcionar un email'))
            return
        
        self.stdout.write(f'Configurando destinatario: {email}')
        if nombre:
            self.stdout.write(f'Nombre: {nombre}')
        self.stdout.write('')
        
        # Obtener alertas
        if solo_activas:
            alertas = ConfiguracionAlerta.objects.filter(activo=True)
        else:
            alertas = ConfiguracionAlerta.objects.all()
        
        agregados = 0
        actualizados = 0
        existentes = 0
        
        for alerta in alertas:
            try:
                # Verificar si ya existe
                destinatario_existente = DestinatarioAlerta.objects.filter(
                    configuracion_alerta=alerta,
                    email=email
                ).first()
                
                if destinatario_existente:
                    if sobrescribir:
                        destinatario_existente.nombre = nombre if nombre else destinatario_existente.nombre
                        destinatario_existente.activo = True
                        destinatario_existente.save()
                        actualizados += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'[ACTUALIZADO] {alerta.get_tipo_alerta_display()}')
                        )
                    else:
                        existentes += 1
                        self.stdout.write(
                            self.style.WARNING(f'[EXISTE] {alerta.get_tipo_alerta_display()} (usa --sobrescribir para actualizar)')
                        )
                else:
                    DestinatarioAlerta.objects.create(
                        configuracion_alerta=alerta,
                        email=email,
                        nombre=nombre if nombre else None,
                        activo=True
                    )
                    agregados += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'[OK] Agregado a: {alerta.get_tipo_alerta_display()}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[ERROR] {alerta.get_tipo_alerta_display()}: {str(e)}')
                )
        
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS('Resumen:'))
        self.stdout.write(f'  Agregados: {agregados}')
        if sobrescribir:
            self.stdout.write(f'  Actualizados: {actualizados}')
        if existentes > 0:
            self.stdout.write(f'  Existentes (no modificados): {existentes}')
        self.stdout.write('')
        self.stdout.write('Configuracion completada!')






