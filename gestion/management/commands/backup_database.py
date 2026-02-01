"""
Comando de gestión para realizar backups de la base de datos.
Soporta SQLite (dumpdata JSON y copia de archivo) y preparado para MySQL/PostgreSQL.
Incluye envío automático a ubicaciones remotas.
"""
import os
import shutil
from pathlib import Path
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from io import StringIO
from gestion.services.backup_remote import BackupRemoteService


class Command(BaseCommand):
    help = 'Realiza backup de la base de datos (JSON y archivo SQLite si aplica)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default=None,
            help='Directorio donde guardar los backups (por defecto: BASE_DIR/backups)',
        )
        parser.add_argument(
            '--keep-days',
            type=int,
            default=30,
            help='Número de días para mantener backups antiguos (por defecto: 30)',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'sqlite', 'both'],
            default='both',
            help='Formato de backup: json, sqlite, o both (por defecto: both)',
        )
        parser.add_argument(
            '--remote',
            action='store_true',
            help='Enviar backup a ubicación remota configurada',
        )
        parser.add_argument(
            '--no-remote',
            action='store_true',
            help='No enviar backup a ubicación remota (sobrescribe configuración)',
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        keep_days = options['keep_days']
        backup_format = options['format']
        send_remote = options.get('remote', False)
        no_remote = options.get('no_remote', False)

        # Determinar directorio de backups
        if output_dir:
            backup_dir = Path(output_dir)
        else:
            backup_dir = Path(settings.BASE_DIR) / 'backups'
        
        # Crear directorio si no existe
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Timestamp para nombres de archivo (usando zona horaria de Colombia)
        ahora = timezone.localtime(timezone.now())
        timestamp = ahora.strftime('%Y%m%d_%H%M%S')
        date_str = ahora.strftime('%Y%m%d')
        
        self.stdout.write(f'Iniciando backup...')
        self.stdout.write(f'Directorio de backups: {backup_dir}')
        
        backups_created = []
        
        # Backup JSON (dumpdata)
        if backup_format in ['json', 'both']:
            json_filename = f'backup_{date_str}_{timestamp}.json'
            json_path = backup_dir / json_filename
            
            try:
                self.stdout.write('Generando backup JSON...')
                with open(json_path, 'w', encoding='utf-8') as f:
                    call_command('dumpdata', '--natural-foreign', '--natural-primary', stdout=f)
                
                file_size = json_path.stat().st_size / (1024 * 1024)  # MB
                success_msg = f'[OK] Backup JSON creado: {json_filename} ({file_size:.2f} MB)'
                self.stdout.write(self.style.SUCCESS(success_msg))
                backups_created.append(json_path)
            except Exception as e:
                error_msg = f'[ERROR] Error creando backup JSON: {str(e)}'
                self.stdout.write(self.style.ERROR(error_msg))
        
        # Backup SQLite (copia de archivo)
        if backup_format in ['sqlite', 'both']:
            db_path = Path(settings.DATABASES['default']['NAME'])
            
            if db_path.exists() and 'sqlite' in settings.DATABASES['default']['ENGINE']:
                sqlite_filename = f'backup_db_{date_str}_{timestamp}.sqlite3'
                sqlite_path = backup_dir / sqlite_filename
                
                try:
                    self.stdout.write('Generando backup SQLite...')
                    shutil.copy2(db_path, sqlite_path)
                    
                    file_size = sqlite_path.stat().st_size / (1024 * 1024)  # MB
                    success_msg = f'[OK] Backup SQLite creado: {sqlite_filename} ({file_size:.2f} MB)'
                    self.stdout.write(self.style.SUCCESS(success_msg))
                    backups_created.append(sqlite_path)
                except Exception as e:
                    error_msg = f'[ERROR] Error creando backup SQLite: {str(e)}'
                    self.stdout.write(self.style.ERROR(error_msg))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        'Base de datos no es SQLite o archivo no existe. '
                        'Solo se creará backup JSON.'
                    )
                )
        
        # Limpiar backups antiguos
        if keep_days > 0:
            self.stdout.write(f'Limpiando backups más antiguos de {keep_days} días...')
            deleted_count = self._clean_old_backups(backup_dir, keep_days)
            if deleted_count > 0:
                success_msg = f'[OK] Eliminados {deleted_count} backups antiguos'
                self.stdout.write(self.style.SUCCESS(success_msg))
            else:
                self.stdout.write('No hay backups antiguos para eliminar')
        
        # Resumen
        if backups_created:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('[OK] Backup completado exitosamente'))
            self.stdout.write(f'Archivos creados: {len(backups_created)}')
            self.stdout.write(f'Ubicacion: {backup_dir}')
            
            # Envío remoto
            if not no_remote and (send_remote or os.environ.get('BACKUP_REMOTE_ENABLED', 'False') == 'True'):
                self.stdout.write('')
                self.stdout.write('Enviando backup a ubicación remota...')
                remote_service = BackupRemoteService()
                
                def on_success(result):
                    self.stdout.write(self.style.SUCCESS(f'[OK] {result.get("message", "Backup enviado exitosamente")}'))
                    if result.get('destination'):
                        self.stdout.write(f'Destino: {result.get("destination")}')
                
                def on_error(result):
                    self.stdout.write(self.style.ERROR(f'[ERROR] {result.get("message", "Error enviando backup")}'))
                
                remote_result = remote_service.send_backup(
                    backups_created,
                    success_callback=on_success,
                    error_callback=on_error
                )
                
                if remote_result.get('skipped'):
                    self.stdout.write(self.style.WARNING('[INFO] Envío remoto deshabilitado'))
        else:
            self.stdout.write(self.style.ERROR('[ERROR] No se pudo crear ningun backup'))
            return
        
        # Información adicional
        self.stdout.write('')
        self.stdout.write('Para restaurar un backup:')
        self.stdout.write('  JSON: python manage.py loaddata backups/backup_YYYYMMDD_HHMMSS.json')
        self.stdout.write('  SQLite: cp backups/backup_db_YYYYMMDD_HHMMSS.sqlite3 db.sqlite3')

    def _clean_old_backups(self, backup_dir, keep_days):
        """Elimina backups más antiguos que keep_days"""
        from datetime import timedelta, datetime
        
        cutoff_date = timezone.localtime(timezone.now()) - timedelta(days=keep_days)
        deleted_count = 0
        
        for backup_file in backup_dir.glob('backup_*'):
            try:
                file_time_naive = datetime.fromtimestamp(backup_file.stat().st_mtime)
                file_time = timezone.make_aware(file_time_naive)
                file_time_local = timezone.localtime(file_time)
                if file_time_local < cutoff_date:
                    backup_file.unlink()
                    deleted_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'No se pudo eliminar {backup_file}: {str(e)}')
                )
        
        return deleted_count

