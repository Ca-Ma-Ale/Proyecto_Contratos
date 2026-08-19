#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! docker network inspect web_proxy >/dev/null 2>&1; then
  docker network create web_proxy >/dev/null
fi

git fetch origin
git checkout main
git pull --ff-only origin main

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate
docker compose -f docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput
docker compose -f docker-compose.prod.yml exec -T web python manage.py check --deploy --fail-level WARNING
docker compose -f docker-compose.prod.yml restart web
docker compose -f docker-compose.prod.yml ps
