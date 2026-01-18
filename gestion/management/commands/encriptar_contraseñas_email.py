"""
Comando para encriptar contraseñas de email existentes en la base de datos.

Uso:
    python manage.py encriptar_contraseñas_email

Este comando:
1. Busca todas las configuraciones de email
2. Verifica si las contraseñas están encriptadas
3. Encripta las que estén en texto plano
4. Guarda los cambios

IMPORTANTE: Asegúrate de tener ENCRYPTION_KEY configurada antes de ejecutar.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from gestion.models import ConfiguracionEmail
from gestion.utils_encryption import encrypt_value, decrypt_value
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Encripta las contraseñas de email que estén en texto plano'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la encriptación sin guardar cambios',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la re-encriptación de todas las contraseñas',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Encriptación de Contraseñas de Email'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Verificar que ENCRYPTION_KEY esté configurada
        try:
            from gestion.utils_encryption import get_encryption_key
            key = get_encryption_key()
            self.stdout.write(self.style.SUCCESS('✓ ENCRYPTION_KEY configurada correctamente'))
        except Exception as e:
            self.stdout.write(self.style.ERROR('✗ Error: ENCRYPTION_KEY no está configurada'))
            self.stdout.write(self.style.ERROR(f'   {str(e)}'))
            self.stdout.write(self.style.WARNING('\nPara generar una clave:'))
            self.stdout.write(self.style.WARNING('   python -c "from gestion.utils_encryption import generate_encryption_key; print(generate_encryption_key())"'))
            self.stdout.write(self.style.WARNING('\nAgrega la clave a tu archivo .env:'))
            self.stdout.write(self.style.WARNING('   ENCRYPTION_KEY=tu_clave_generada'))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  MODO DRY-RUN: No se guardarán cambios'))
        
        configuraciones = ConfiguracionEmail.objects.all()
        
        if not configuraciones.exists():
            self.stdout.write(self.style.WARNING('\n⚠️  No hay configuraciones de email en la base de datos'))
            return
        
        self.stdout.write(f'\nEncontradas {configuraciones.count()} configuración(es) de email\n')
        
        encriptadas = 0
        ya_encriptadas = 0
        errores = 0
        
        for config in configuraciones:
            self.stdout.write(f'Procesando: {config.nombre} ({config.email_from})')
            
            if not config.email_host_password:
                self.stdout.write(self.style.WARNING('  ⚠️  Sin contraseña configurada, omitiendo'))
                continue
            
            # Intentar desencriptar para verificar si ya está encriptada
            try:
                decrypt_value(config.email_host_password)
                # Si llegamos aquí, ya está encriptada
                if force:
                    self.stdout.write(self.style.WARNING('  ⚠️  Ya encriptada, pero --force activado'))
                    # Obtener la contraseña actual y re-encriptar
                    try:
                        password_actual = config.get_password()
                        if not dry_run:
                            config.set_password(password_actual)
                            config.save(update_fields=['email_host_password'])
                        self.stdout.write(self.style.SUCCESS('  ✓ Re-encriptada'))
                        encriptadas += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  ✗ Error re-encriptando: {e}'))
                        errores += 1
                else:
                    self.stdout.write(self.style.SUCCESS('  ✓ Ya está encriptada'))
                    ya_encriptadas += 1
            except (ValueError, Exception):
                # No está encriptada, encriptar ahora
                try:
                    password_plano = config.email_host_password
                    if not dry_run:
                        config.set_password(password_plano)
                        config.save(update_fields=['email_host_password'])
                    self.stdout.write(self.style.SUCCESS('  ✓ Encriptada exitosamente'))
                    encriptadas += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Error encriptando: {e}'))
                    errores += 1
        
        # Resumen
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('Resumen:'))
        self.stdout.write(self.style.SUCCESS(f'  ✓ Encriptadas: {encriptadas}'))
        self.stdout.write(self.style.SUCCESS(f'  ✓ Ya encriptadas: {ya_encriptadas}'))
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'  ✗ Errores: {errores}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: No se guardaron cambios'))
            self.stdout.write(self.style.WARNING('   Ejecuta sin --dry-run para aplicar cambios'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Proceso completado'))
        
        self.stdout.write(self.style.SUCCESS('=' * 60))

