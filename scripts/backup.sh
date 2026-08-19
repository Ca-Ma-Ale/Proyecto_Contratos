#!/usr/bin/env bash
# Respaldo de la base de datos MySQL y de media del sistema de contratos.
#
# Uso (en el VPS, desde cualquier directorio):
#   /opt/proyecto-contratos/scripts/backup.sh [dias_retencion]   (por defecto 14)
#
# - La contraseña se pasa por variable de entorno (MYSQL_PWD), no en la linea
#   de comandos, para que no quede visible en `ps` (CWE-214).
# - umask 077: los archivos generados solo los lee root.
# - Borra los respaldos con mas de N dias para no llenar el disco.
set -euo pipefail
umask 077

cd "$(dirname "$0")/.."

dias_retencion="${1:-14}"
timestamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="backups/${timestamp}"
mkdir -p "$backup_dir"

leer_env() { grep -E "^$1=" .env | tail -n 1 | cut -d= -f2-; }
database_name="$(leer_env DATABASE_NAME)"
mysql_root_password="$(leer_env MYSQL_ROOT_PASSWORD)"

if [[ -z "$database_name" || -z "$mysql_root_password" ]]; then
  echo "ERROR: DATABASE_NAME o MYSQL_ROOT_PASSWORD no definidos en .env" >&2
  exit 1
fi

docker compose -f docker-compose.prod.yml exec -T \
  -e MYSQL_PWD="$mysql_root_password" mysql \
  mysqldump -u root --single-transaction --routines --triggers "$database_name" \
  | gzip > "${backup_dir}/database.sql.gz"

tar -czf "${backup_dir}/media.tar.gz" -C deploy_data media 2>/dev/null || true

# Sanidad minima: el dump no debe estar vacio
if [[ ! -s "${backup_dir}/database.sql.gz" ]]; then
  echo "ERROR: el respaldo de la base de datos quedo vacio" >&2
  exit 1
fi

# Retencion: eliminar respaldos automaticos antiguos (solo carpetas con formato de fecha)
find backups -maxdepth 1 -mindepth 1 -type d -regextype posix-extended \
  -regex '.*/[0-9]{8}-[0-9]{6}$' -mtime +"$dias_retencion" -exec rm -rf {} +

echo "$(date '+%F %T') Backup creado en ${backup_dir} ($(du -sh "$backup_dir" | cut -f1)); retencion ${dias_retencion} dias"
