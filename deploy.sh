#!/usr/bin/env bash
# Radar release tooling. No database is restored or downgraded automatically.
set -Eeuo pipefail
umask 077
DEPLOY_DIR="${RADAR_DEPLOY_DIR:-/opt/radar}"
BACKUP_DIR="${RADAR_BACKUP_DIR:-/opt/backups/radar}"
COMPOSE_FILE="${RADAR_COMPOSE_FILE:-docker-compose.prod.yml}"
LOG_FILE="${RADAR_DEPLOY_LOG:-/var/log/radar-deploy.log}"

compose() { docker compose --project-directory "$DEPLOY_DIR" -f "$DEPLOY_DIR/$COMPOSE_FILE" "$@"; }
log() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$LOG_FILE"; }
spinner() {
    local pid=$1 message=$2 result=0
    if wait "$pid"; then
        printf '%s ✓\n' "$message"
    else
        result=$?
        printf '%s : échec (code %s)\n' "$message" "$result" >&2
        return "$result"
    fi
}
pre_flight_check() {
    command -v docker >/dev/null
    docker compose version >/dev/null
    test -d "$DEPLOY_DIR/.git"
    test -f "$DEPLOY_DIR/.env" || { echo 'Configuration .env requise ; aucun exemple ne sera activé automatiquement.' >&2; return 1; }
    compose config --quiet
}
start_database() { compose up -d --wait --wait-timeout 90 postgres redis; }
create_backup() {
    mkdir -p "$BACKUP_DIR"
    chmod 700 "$BACKUP_DIR"
    local archive temporary
    archive="$BACKUP_DIR/radar_$(date -u +%Y%m%dT%H%M%S)_${RANDOM}.dump"
    temporary="$archive.partial"
    if ! compose exec -T postgres sh -ec 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$temporary"; then
        rm -f "$temporary"
        echo 'Échec de sauvegarde : déploiement interrompu.' >&2
        return 1
    fi
    if ! test -s "$temporary" || ! compose exec -T postgres pg_restore --list < "$temporary" > /dev/null; then
        rm -f "$temporary"
        echo 'Archive PostgreSQL invalide : déploiement interrompu.' >&2
        return 1
    fi
    mv "$temporary" "$archive"
    sha256sum "$archive" > "$archive.sha256"
    git -C "$DEPLOY_DIR" rev-parse HEAD > "$archive.commit"
    compose exec -T postgres sh -ec 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version ORDER BY version_num"' > "$archive.revisions" || {
        echo 'Révision de schéma inconnue : vérifier la base avant migration.' >&2; return 1;
    }
    # Never prune the only recoverable data automatically. Offsite retention is an operator policy.
    log "Sauvegarde vérifiée : $archive. Une restauration isolée reste requise."
}
pull_latest() {
    test -z "$(git -C "$DEPLOY_DIR" status --porcelain)" || {
        echo 'Modifications locales : déploiement interrompu, aucun stash automatique.' >&2; return 1;
    }
    git -C "$DEPLOY_DIR" fetch origin "${RADAR_DEPLOY_REF:-main}"
    git -C "$DEPLOY_DIR" checkout --detach FETCH_HEAD
}
build_images() { compose build; }
run_migrations() {
    # Uses the newly built image, never the old running backend image.
    compose run --rm --no-deps backend alembic upgrade head
}
deploy_services() { compose up -d --remove-orphans; }
health_check() {
    # All checks are internal: the production stack does not publish 8000/3000.
    compose exec -T backend python -m app.cli.check_runtime
    compose exec -T frontend node -e 'fetch("http://127.0.0.1:3000/login").then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))'
    # Verify workers really consume all declared queues, without logging payloads.
    compose exec -T worker python -m app.cli.check_queues
}
rollback() {
    echo 'Retour automatique refusé : le code, les images et le schéma doivent correspondre.' >&2
    echo 'Suivre docs/refonte/RELEASE-RECOVERY.md avec une archive restaurée et validée en environnement isolé.' >&2
    return 1
}
release() {
    pre_flight_check
    start_database
    # An empty installation has no customer history to back up. Existing schema must be backed up.
    local existing
    existing=$(compose exec -T postgres sh -ec 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema = '\''public'\'' AND table_type = '\''BASE TABLE'\''"')
    if [ "$existing" != '0' ]; then create_backup; fi
    pull_latest
    python3 "$DEPLOY_DIR/scripts/check_release.py"
    build_images
    run_migrations
    deploy_services
    local ready=false
    for attempt in {1..15}; do
        if health_check; then ready=true; break; fi
        sleep 2
    done
    [ "$ready" = true ] || { log 'Échec de readiness : livraison non validée.'; return 1; }
    log "Livraison validée : $(git -C "$DEPLOY_DIR" rev-parse HEAD)"
}
main() {
    case "${1:---help}" in
        --full|--quick) release ;;
        --backup) pre_flight_check; create_backup ;;
        --rollback) rollback ;;
        --status) compose ps ;;
        --logs) compose logs --tail 100 -f ;;
        --help|-h) printf '%s\n' 'Usage: deploy.sh --full|--quick|--backup|--status|--logs|--rollback' 'Les deux modes de livraison reconstruisent et migrent ; aucun raccourci de sécurité.' ;;
        *) echo 'Option inconnue' >&2; return 2 ;;
    esac
}
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
