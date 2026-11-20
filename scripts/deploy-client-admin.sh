#!/usr/bin/env bash
# Run after checking out the reviewed feature branch in /opt/radar.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then exec sudo bash "$0" "$@"; fi
cd /opt/radar
sudo python3 scripts/prepare_security_config.py
radar_compose() { sudo docker compose -f compose.server.yml -f compose.mcp.yml -f ops/security/compose.security.yml "$@"; }
radar_stamp=$(date -u +%Y%m%dT%H%M%SZ)
radar_backup="/opt/radar-deployment-backups/client-admin-$radar_stamp"
sudo install -d -m 700 "$radar_backup"
# Public certificate only; the offline private key must never be needed for backup.
if [ -f /etc/radar-operations.env ]; then
  set -a
  source /etc/radar-operations.env
  set +a
fi
sudo --preserve-env=RADAR_BACKUP_CERTIFICATE python3 scripts/security_preflight.py
sudo --preserve-env=RADAR_BACKUP_CERTIFICATE,RADAR_BACKUP_REMOTE python3 scripts/operations.py backup --directory "$radar_backup"
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
radar_compose exec -T backend python -m app.core.credential_cache
radar_compose ps backend worker scheduler frontend
printf '\nSauvegarde : %s\nVérifiez connexion, A2F, sélection du workspace et /admin/clients.\n' "$radar_backup"
