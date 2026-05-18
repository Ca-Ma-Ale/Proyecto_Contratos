import getpass

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


USUARIOS = [
    {'username': 'Operaciones_Avchile',  'area': 'Operaciones'},
    {'username': 'Compras_Avchile',      'area': 'Compras'},
    {'username': 'Contabilidad_Avchile', 'area': 'Contabilidad'},
    {'username': 'Seguridad_Avchile',    'area': 'Seguridad y Parqueadero'},
    {'username': 'Mercadeo_Avchile',     'area': 'Mercadeo'},
    {'username': 'Gerencia_Avchile',     'area': 'Gerencia'},
]


class Command(BaseCommand):
    help = 'Crea los usuarios por área de Avenida Chile (solicita contraseña por consola)'

    def handle(self, *args, **options):
        creados = 0
        existentes = 0

        for datos in USUARIOS:
            if User.objects.filter(username=datos['username']).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"  Ya existe: {datos['username']} ({datos['area']})"
                    )
                )
                existentes += 1
                continue

            self.stdout.write(f"\nUsuario: {datos['username']} ({datos['area']})")
            while True:
                password = getpass.getpass('  Contraseña: ')
                confirmacion = getpass.getpass('  Confirmar:  ')
                if password == confirmacion:
                    break
                self.stdout.write(self.style.ERROR('  Las contraseñas no coinciden, intente de nuevo.'))

            User.objects.create_user(username=datos['username'], password=password)
            self.stdout.write(self.style.SUCCESS(f"  Creado: {datos['username']}"))
            creados += 1

        self.stdout.write('')
        self.stdout.write(f'Creados: {creados}  |  Ya existían: {existentes}')
