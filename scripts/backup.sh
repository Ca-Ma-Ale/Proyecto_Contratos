#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

timestamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="backups/${timestamp}"
mkdir -p "$backup_dir"

database_name="$(grep -E '^DATABASE_NAME=' .env | tail -n 1 | cut -d= -f2-)"
mysql_root_password="$(grep -E '^MYSQL_ROOT_PASSWORD=' .env | tail -n 1 | cut -d= -f2-)"

docker compose -f docker-compose.prod.yml exec -T mysql \
  mysqldump -u root -p"${mysql_root_password}" "${database_name}" \
  > "${backup_dir}/database.sql"

tar -czf "${backup_dir}/media.tar.gz" deploy_data/media 2>/dev/null || true

echo "Backup creado en ${backup_dir}"
