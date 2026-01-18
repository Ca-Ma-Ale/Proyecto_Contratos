#!/bin/bash
# Script para automatizar backups diarios en Linux/Unix
# Uso: Agregar a crontab para ejecución diaria
# Incluye envío automático a ubicaciones remotas configuradas

# Configuración
PROJECT_DIR="/ruta/al/proyecto"  # CAMBIAR: Ruta al proyecto
VENV_DIR="$PROJECT_DIR/venv"     # Ruta al entorno virtual
BACKUP_DIR="$PROJECT_DIR/backups"
KEEP_DAYS=30

# Activar entorno virtual
source "$VENV_DIR/bin/activate"

# Cambiar al directorio del proyecto
cd "$PROJECT_DIR"

# Ejecutar comando de backup con envío remoto automático
# El envío remoto se controla mediante variables de entorno en .env
# Para habilitar: BACKUP_REMOTE_ENABLED=True en .env
python manage.py backup_database --keep-days "$KEEP_DAYS" --format both --remote

# Opcional: Comprimir backups antiguos
# find "$BACKUP_DIR" -name "backup_*.json" -mtime +7 -exec gzip {} \;
# find "$BACKUP_DIR" -name "backup_db_*.sqlite3" -mtime +7 -exec gzip {} \;

echo "Backup diario completado: $(date)"

