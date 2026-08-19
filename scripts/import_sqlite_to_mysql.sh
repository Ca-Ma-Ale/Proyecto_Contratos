#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ "$#" -ne 1 ]; then
  echo "Uso: scripts/import_sqlite_to_mysql.sh ruta/al/db.sqlite3"
  exit 1
fi

source_sqlite="$1"
if [ ! -f "$source_sqlite" ]; then
  echo "No existe el SQLite origen: $source_sqlite"
  exit 1
fi

if [ ! -f .env ]; then
  echo "Falta .env."
  exit 1
fi

get_env() {
  grep -E "^$1=" .env | tail -n 1 | cut -d= -f2-
}

database_name="$(get_env DATABASE_NAME)"
mysql_root_password="$(get_env MYSQL_ROOT_PASSWORD)"

if [ -z "$database_name" ] || [ -z "$mysql_root_password" ]; then
  echo "DATABASE_NAME y MYSQL_ROOT_PASSWORD deben existir en .env."
  exit 1
fi

timestamp="$(date +%Y%m%d-%H%M%S)"
import_dir="backups/sqlite-import-${timestamp}"
mkdir -p "$import_dir"

cp "$source_sqlite" "$import_dir/source.sqlite3"

docker compose -f docker-compose.prod.yml up -d mysql web

docker compose -f docker-compose.prod.yml exec -T mysql \
  mysqldump -u root -p"${mysql_root_password}" "${database_name}" \
  > "$import_dir/mysql-before-import.sql" || true

docker compose -f docker-compose.prod.yml exec -T mysql \
  mysql -u root -p"${mysql_root_password}" \
  -e "DROP DATABASE IF EXISTS \`${database_name}\`; CREATE DATABASE \`${database_name}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

docker compose -f docker-compose.prod.yml cp "$import_dir/source.sqlite3" web:/app/db.sqlite3

docker compose -f docker-compose.prod.yml exec -T web \
  env DATABASE_NAME= DEBUG=True python manage.py migrate

docker compose -f docker-compose.prod.yml exec -T web \
  env DATABASE_NAME= DEBUG=True python manage.py dumpdata \
    --natural-foreign \
    --natural-primary \
    --exclude contenttypes \
    --exclude auth.permission \
    --exclude admin.logentry \
    --exclude sessions.session \
    --output /tmp/sqlite-data.json

docker compose -f docker-compose.prod.yml cp web:/tmp/sqlite-data.json "$import_dir/sqlite-data.json"

docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate
docker compose -f docker-compose.prod.yml cp "$import_dir/sqlite-data.json" web:/tmp/sqlite-data.json
docker compose -f docker-compose.prod.yml exec -T web python manage.py loaddata /tmp/sqlite-data.json
docker compose -f docker-compose.prod.yml exec -T web python manage.py check --deploy
docker compose -f docker-compose.prod.yml restart web

echo "Importacion SQLite -> MySQL finalizada."
echo "Respaldo y fixture en: $import_dir"
