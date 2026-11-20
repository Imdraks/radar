#!/usr/bin/env bash
# Run after checking out the reviewed feature branch in /opt/radar.
set -euo pipefail
cd /opt/radar
radar_compose() { sudo docker compose -f compose.server.yml -f compose.mcp.yml "$@"; }
radar_stamp=$(date -u +%Y%m%dT%H%M%SZ)
radar_backup="/opt/radar-deployment-backups/client-admin-$radar_stamp"
sudo install -d -m 700 "$radar_backup"
# No stdin attachment; fail rather than wait forever on a locked database.
radar_compose exec -T postgres sh -c \
  'exec pg_dump --lock-wait-timeout=30s -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-postgres}"' \
  </dev/null | gzip | sudo tee "$radar_backup/postgres.sql.gz" >/dev/null
sudo gzip -t "$radar_backup/postgres.sql.gz"
sudo sh -c 'gzip -dc "$1" | head -c 1 | grep -q .' sh "$radar_backup/postgres.sql.gz"
for radar_service in backend frontend; do
  radar_image=$(sudo docker inspect --format '{{.Image}}' "radar-${radar_service}-1")
  sudo docker image tag "$radar_image" "radar-${radar_service}:before-client-admin-$radar_stamp"
done
sudo git rev-parse HEAD | sudo tee "$radar_backup/source-commit.txt" >/dev/null
radar_compose build backend frontend
# Schema must exist before the new API or worker is started.
radar_compose run --rm --no-deps backend alembic upgrade head
radar_compose up -d --no-deps backend worker scheduler frontend
radar_compose exec -T backend alembic current
radar_compose ps backend worker scheduler frontend
printf '\nSauvegarde : %s\nVérifiez /admin/clients et une invitation de test autorisée.\n' "$radar_backup"
