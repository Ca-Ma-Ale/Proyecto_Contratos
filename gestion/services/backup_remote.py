"""
Servicio para envío remoto de backups a diferentes destinos.
Soporta: OneDrive, Google Drive, servidor remoto (SFTP/SCP), AWS S3, y más.
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from django.conf import settings
from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend


class BackupRemoteService:
    """Servicio para enviar backups a ubicaciones remotas"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el servicio de backup remoto.
        
        Args:
            config: Diccionario con configuración. Si es None, lee de variables de entorno.
        """
        self.config = config or self._load_config_from_env()
    
    def _load_config_from_env(self) -> Dict[str, Any]:
        """Carga configuración desde variables de entorno"""
        return {
            'enabled': os.environ.get('BACKUP_REMOTE_ENABLED', 'False') == 'True',
            'destination': os.environ.get('BACKUP_REMOTE_DESTINATION', 'onedrive'),
            'onedrive_path': os.environ.get('BACKUP_ONEDRIVE_PATH', ''),
            'google_drive_path': os.environ.get('BACKUP_GOOGLE_DRIVE_PATH', ''),
            'sftp_host': os.environ.get('BACKUP_SFTP_HOST', ''),
            'sftp_user': os.environ.get('BACKUP_SFTP_USER', ''),
            'sftp_password': os.environ.get('BACKUP_SFTP_PASSWORD', ''),
            'sftp_path': os.environ.get('BACKUP_SFTP_PATH', '/backups/contratos'),
            'sftp_port': int(os.environ.get('BACKUP_SFTP_PORT', '22')),
            'aws_s3_bucket': os.environ.get('BACKUP_AWS_S3_BUCKET', ''),
            'aws_access_key': os.environ.get('BACKUP_AWS_ACCESS_KEY', ''),
            'aws_secret_key': os.environ.get('BACKUP_AWS_SECRET_KEY', ''),
            'aws_region': os.environ.get('BACKUP_AWS_REGION', 'us-east-1'),
            'email_notifications': os.environ.get('BACKUP_EMAIL_NOTIFICATIONS', 'False') == 'True',
            'email_recipients': os.environ.get('BACKUP_EMAIL_RECIPIENTS', '').split(',') if os.environ.get('BACKUP_EMAIL_RECIPIENTS') else [],
        }
    
    def send_backup(self, backup_files: List[Path], success_callback=None, error_callback=None) -> Dict[str, Any]:
        """
        Envía backups a la ubicación remota configurada.
        
        Args:
            backup_files: Lista de archivos de backup a enviar
            success_callback: Función a llamar en caso de éxito
            error_callback: Función a llamar en caso de error
            
        Returns:
            Dict con resultado de la operación
        """
        if not self.config.get('enabled'):
            return {
                'success': False,
                'message': 'Backup remoto deshabilitado',
                'skipped': True
            }
        
        destination = self.config.get('destination', 'onedrive').lower()
        
        try:
            if destination == 'onedrive':
                result = self._send_to_onedrive(backup_files)
            elif destination == 'google_drive':
                result = self._send_to_google_drive(backup_files)
            elif destination == 'sftp' or destination == 'scp':
                result = self._send_to_sftp(backup_files)
            elif destination == 's3' or destination == 'aws':
                result = self._send_to_s3(backup_files)
            elif destination == 'local_copy':
                result = self._send_to_local_copy(backup_files)
            else:
                result = {
                    'success': False,
                    'message': f'Destino no soportado: {destination}'
                }
            
            if result.get('success') and success_callback:
                success_callback(result)
            elif not result.get('success') and error_callback:
                error_callback(result)
            
            if self.config.get('email_notifications'):
                self._send_notification(result, backup_files)
            
            return result
            
        except Exception as e:
            error_result = {
                'success': False,
                'message': f'Error enviando backup: {str(e)}',
                'error': str(e)
            }
            if error_callback:
                error_callback(error_result)
            if self.config.get('email_notifications'):
                self._send_notification(error_result, backup_files)
            return error_result
    
    def _send_to_onedrive(self, backup_files: List[Path]) -> Dict[str, Any]:
        """Envía backups a OneDrive usando copia directa"""
        onedrive_path = self.config.get('onedrive_path')
        
        if not onedrive_path:
            return {
                'success': False,
                'message': 'Ruta de OneDrive no configurada'
            }
        
        onedrive_dir = Path(onedrive_path)
        if not onedrive_dir.exists():
            return {
                'success': False,
                'message': f'Directorio de OneDrive no existe: {onedrive_path}'
            }
        
        backup_dir = onedrive_dir / 'backups' / 'contratos'
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        copied_files = []
        for backup_file in backup_files:
            try:
                dest_file = backup_dir / backup_file.name
                shutil.copy2(backup_file, dest_file)
                copied_files.append(str(dest_file))
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Error copiando {backup_file.name}: {str(e)}'
                }
        
        return {
            'success': True,
            'message': f'Backups copiados a OneDrive: {len(copied_files)} archivos',
            'files': copied_files,
            'destination': str(backup_dir)
        }
    
    def _send_to_google_drive(self, backup_files: List[Path]) -> Dict[str, Any]:
        """Envía backups a Google Drive usando rclone o copia directa"""
        google_drive_path = self.config.get('google_drive_path')
        
        if not google_drive_path:
            return {
                'success': False,
                'message': 'Ruta de Google Drive no configurada'
            }
        
        google_drive_dir = Path(google_drive_path)
        if not google_drive_dir.exists():
            return {
                'success': False,
                'message': f'Directorio de Google Drive no existe: {google_drive_path}'
            }
        
        backup_dir = google_drive_dir / 'backups' / 'contratos'
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        copied_files = []
        for backup_file in backup_files:
            try:
                dest_file = backup_dir / backup_file.name
                shutil.copy2(backup_file, dest_file)
                copied_files.append(str(dest_file))
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Error copiando {backup_file.name}: {str(e)}'
                }
        
        return {
            'success': True,
            'message': f'Backups copiados a Google Drive: {len(copied_files)} archivos',
            'files': copied_files,
            'destination': str(backup_dir)
        }
    
    def _send_to_sftp(self, backup_files: List[Path]) -> Dict[str, Any]:
        """Envía backups a servidor remoto usando SFTP/SCP"""
        host = self.config.get('sftp_host')
        user = self.config.get('sftp_user')
        password = self.config.get('sftp_password')
        remote_path = self.config.get('sftp_path', '/backups/contratos')
        port = self.config.get('sftp_port', 22)
        
        if not all([host, user]):
            return {
                'success': False,
                'message': 'Configuración SFTP incompleta (host y usuario requeridos)'
            }
        
        try:
            if password:
                sshpass_available = self._check_command('sshpass')
                if not sshpass_available:
                    return {
                        'success': False,
                        'message': 'sshpass no está instalado. Instala con: sudo apt install sshpass'
                    }
            
            copied_files = []
            for backup_file in backup_files:
                try:
                    if password:
                        cmd = [
                            'sshpass', '-p', password,
                            'scp', '-P', str(port), '-o', 'StrictHostKeyChecking=no',
                            str(backup_file),
                            f'{user}@{host}:{remote_path}/'
                        ]
                    else:
                        cmd = [
                            'scp', '-P', str(port), '-o', 'StrictHostKeyChecking=no',
                            str(backup_file),
                            f'{user}@{host}:{remote_path}/'
                        ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.returncode != 0:
                        return {
                            'success': False,
                            'message': f'Error en SCP: {result.stderr}'
                        }
                    
                    copied_files.append(f'{host}:{remote_path}/{backup_file.name}')
                    
                except subprocess.TimeoutExpired:
                    return {
                        'success': False,
                        'message': f'Timeout enviando {backup_file.name}'
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'message': f'Error enviando {backup_file.name}: {str(e)}'
                    }
            
            return {
                'success': True,
                'message': f'Backups enviados por SFTP: {len(copied_files)} archivos',
                'files': copied_files,
                'destination': f'{user}@{host}:{remote_path}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error en envío SFTP: {str(e)}'
            }
    
    def _send_to_s3(self, backup_files: List[Path]) -> Dict[str, Any]:
        """Envía backups a AWS S3"""
        bucket = self.config.get('aws_s3_bucket')
        access_key = self.config.get('aws_access_key')
        secret_key = self.config.get('aws_secret_key')
        region = self.config.get('aws_region', 'us-east-1')
        
        if not all([bucket, access_key, secret_key]):
            return {
                'success': False,
                'message': 'Configuración AWS S3 incompleta'
            }
        
        aws_cli_available = self._check_command('aws')
        if not aws_cli_available:
            return {
                'success': False,
                'message': 'AWS CLI no está instalado. Instala con: pip install awscli'
            }
        
        try:
            os.environ['AWS_ACCESS_KEY_ID'] = access_key
            os.environ['AWS_SECRET_ACCESS_KEY'] = secret_key
            os.environ['AWS_DEFAULT_REGION'] = region
            
            uploaded_files = []
            for backup_file in backup_files:
                try:
                    s3_key = f'backups/contratos/{backup_file.name}'
                    cmd = [
                        'aws', 's3', 'cp',
                        str(backup_file),
                        f's3://{bucket}/{s3_key}',
                        '--region', region
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=600
                    )
                    
                    if result.returncode != 0:
                        return {
                            'success': False,
                            'message': f'Error subiendo a S3: {result.stderr}'
                        }
                    
                    uploaded_files.append(f's3://{bucket}/{s3_key}')
                    
                except subprocess.TimeoutExpired:
                    return {
                        'success': False,
                        'message': f'Timeout subiendo {backup_file.name}'
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'message': f'Error subiendo {backup_file.name}: {str(e)}'
                    }
            
            return {
                'success': True,
                'message': f'Backups subidos a S3: {len(uploaded_files)} archivos',
                'files': uploaded_files,
                'destination': f's3://{bucket}/backups/contratos'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error en envío S3: {str(e)}'
            }
    
    def _send_to_local_copy(self, backup_files: List[Path]) -> Dict[str, Any]:
        """Copia backups a otra ubicación local (útil para sincronización con servicios de nube)"""
        local_path = self.config.get('local_copy_path', '')
        
        if not local_path:
            return {
                'success': False,
                'message': 'Ruta de copia local no configurada'
            }
        
        backup_dir = Path(local_path)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        copied_files = []
        for backup_file in backup_files:
            try:
                dest_file = backup_dir / backup_file.name
                shutil.copy2(backup_file, dest_file)
                copied_files.append(str(dest_file))
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Error copiando {backup_file.name}: {str(e)}'
                }
        
        return {
            'success': True,
            'message': f'Backups copiados localmente: {len(copied_files)} archivos',
            'files': copied_files,
            'destination': str(backup_dir)
        }
    
    def _check_command(self, command: str) -> bool:
        """Verifica si un comando está disponible en el sistema"""
        try:
            subprocess.run(
                [command, '--version'],
                capture_output=True,
                timeout=5
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _send_notification(self, result: Dict[str, Any], backup_files: List[Path]) -> None:
        """Envía notificación por email sobre el resultado del backup"""
        recipients = self.config.get('email_recipients', [])
        if not recipients:
            return
        
        try:
            subject = 'Backup Automático - ' + ('Éxito' if result.get('success') else 'Error')
            
            message_lines = [
                f'Resultado del backup automático:',
                f'Estado: {"Éxito" if result.get("success") else "Error"}',
                f'Mensaje: {result.get("message", "N/A")}',
                '',
                f'Archivos procesados: {len(backup_files)}',
            ]
            
            if result.get('files'):
                message_lines.append('Archivos enviados:')
                for file in result.get('files', []):
                    message_lines.append(f'  - {file}')
            
            if result.get('destination'):
                message_lines.append(f'Destino: {result.get("destination")}')
            
            if result.get('error'):
                message_lines.append(f'Error: {result.get("error")}')
            
            message = '\n'.join(message_lines)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else None,
                recipient_list=recipients,
                fail_silently=True
            )
        except Exception as e:
            pass

















