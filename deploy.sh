#!/bin/bash
#
# 🚀 RADAR - Script de Déploiement Automatisé VPS
# ================================================
# Usage: ./deploy.sh [options]
#
# Options:
#   --quick       Déploiement rapide (pull + restart seulement)
#   --full        Déploiement complet (rebuild + migrations)
#   --rollback    Rollback vers le commit précédent
#   --status      Afficher le statut des services
#   --logs        Afficher les logs en temps réel
#   --backup      Créer un backup de la base de données
#

set -e  # Exit on error

# ═══════════════════════════════════════════════════════════════
# 🎨 CONFIGURATION
# ═══════════════════════════════════════════════════════════════

DEPLOY_DIR="/opt/radar"
BACKUP_DIR="/opt/backups/radar"
LOG_FILE="/var/log/radar-deploy.log"
COMPOSE_FILE="docker-compose.prod.yml"
HEALTH_URL="http://localhost:8000/health"
FRONTEND_URL="http://localhost:3000"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ═══════════════════════════════════════════════════════════════
# 📝 FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════

log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

banner() {
    echo -e "${PURPLE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║   ██████╗  █████╗ ██████╗  █████╗ ██████╗                    ║"
    echo "║   ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗                   ║"
    echo "║   ██████╔╝███████║██║  ██║███████║██████╔╝                   ║"
    echo "║   ██╔══██╗██╔══██║██║  ██║██╔══██║██╔══██╗                   ║"
    echo "║   ██║  ██║██║  ██║██████╔╝██║  ██║██║  ██║                   ║"
    echo "║   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝                   ║"
    echo "║                                                              ║"
    echo "║              🚀 Deployment Automation System                 ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

spinner() {
    local pid=$1
    local message=$2
    local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0
    while kill -0 $pid 2>/dev/null; do
        i=$(( (i+1) % 10 ))
        printf "\r${CYAN}${message} ${spin:$i:1}${NC}"
        sleep 0.1
    done
    printf "\r${GREEN}${message} ✓${NC}\n"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}❌ Ce script doit être exécuté en tant que root${NC}"
        exit 1
    fi
}

# ═══════════════════════════════════════════════════════════════
# 🔍 VÉRIFICATIONS PRÉ-DÉPLOIEMENT
# ═══════════════════════════════════════════════════════════════

pre_flight_check() {
    echo -e "\n${BLUE}🔍 Vérifications pré-déploiement...${NC}\n"
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker n'est pas installé${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Docker installé: $(docker --version | cut -d' ' -f3)"
    
    # Vérifier Docker Compose
    if ! command -v docker compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose n'est pas installé${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Docker Compose installé"
    
    # Vérifier l'espace disque
    local available=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available" -lt 5 ]; then
        echo -e "${YELLOW}⚠️  Espace disque faible: ${available}GB disponible${NC}"
    else
        echo -e "${GREEN}✓${NC} Espace disque: ${available}GB disponible"
    fi
    
    # Vérifier la mémoire
    local mem_available=$(free -m | awk 'NR==2 {print $7}')
    echo -e "${GREEN}✓${NC} Mémoire disponible: ${mem_available}MB"
    
    # Vérifier le répertoire de déploiement
    if [ ! -d "$DEPLOY_DIR" ]; then
        echo -e "${YELLOW}⚠️  Création du répertoire $DEPLOY_DIR${NC}"
        mkdir -p "$DEPLOY_DIR"
    fi
    echo -e "${GREEN}✓${NC} Répertoire de déploiement: $DEPLOY_DIR"
    
    # Vérifier .env
    if [ ! -f "$DEPLOY_DIR/.env" ]; then
        echo -e "${YELLOW}⚠️  Fichier .env manquant - copie de .env.example${NC}"
        [ -f "$DEPLOY_DIR/.env.example" ] && cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"
    fi
    echo -e "${GREEN}✓${NC} Configuration .env présente"
    
    echo ""
}

# ═══════════════════════════════════════════════════════════════
# 💾 BACKUP
# ═══════════════════════════════════════════════════════════════

create_backup() {
    echo -e "\n${BLUE}💾 Création du backup...${NC}\n"
    
    mkdir -p "$BACKUP_DIR"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="radar_backup_${timestamp}"
    
    # Backup de la base de données
    echo -e "${CYAN}📦 Backup PostgreSQL...${NC}"
    docker compose -f "$DEPLOY_DIR/$COMPOSE_FILE" exec -T postgres \
        pg_dump -U radar radar_db | gzip > "$BACKUP_DIR/${backup_name}_db.sql.gz" &
    spinner $! "Backup base de données"
    
    # Backup du commit actuel
    cd "$DEPLOY_DIR"
    local current_commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    echo "$current_commit" > "$BACKUP_DIR/${backup_name}_commit.txt"
    
    # Nettoyer les anciens backups (garder les 7 derniers)
    ls -t "$BACKUP_DIR"/*_db.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm -f
    
    echo -e "${GREEN}✓${NC} Backup créé: ${backup_name}"
    log "INFO" "Backup créé: ${backup_name}"
}

# ═══════════════════════════════════════════════════════════════
# 🔄 DÉPLOIEMENT
# ═══════════════════════════════════════════════════════════════

pull_latest() {
    echo -e "\n${BLUE}📥 Récupération des dernières modifications...${NC}\n"
    
    cd "$DEPLOY_DIR"
    
    # Stash local changes if any
    git stash --quiet 2>/dev/null || true
    
    # Pull latest
    git fetch origin main
    local behind=$(git rev-list HEAD..origin/main --count)
    
    if [ "$behind" -gt 0 ]; then
        echo -e "${CYAN}📦 $behind nouveau(x) commit(s) à télécharger${NC}"
        git pull origin main &
        spinner $! "Téléchargement"
        log "INFO" "Pulled $behind new commits"
    else
        echo -e "${GREEN}✓${NC} Déjà à jour"
    fi
}

build_images() {
    echo -e "\n${BLUE}🔨 Construction des images Docker...${NC}\n"
    
    cd "$DEPLOY_DIR"
    
    docker compose -f "$COMPOSE_FILE" build --no-cache &
    spinner $! "Build en cours"
    
    log "INFO" "Docker images built successfully"
}

run_migrations() {
    echo -e "\n${BLUE}🗃️  Exécution des migrations...${NC}\n"
    
    cd "$DEPLOY_DIR"
    
    # Attendre que la base de données soit prête
    echo -e "${CYAN}⏳ Attente de PostgreSQL...${NC}"
    local retries=30
    while [ $retries -gt 0 ]; do
        if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U radar &>/dev/null; then
            break
        fi
        retries=$((retries - 1))
        sleep 1
    done
    
    # Exécuter les migrations Alembic
    docker compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head &
    spinner $! "Migrations"
    
    log "INFO" "Database migrations completed"
}

deploy_services() {
    echo -e "\n${BLUE}🚀 Démarrage des services...${NC}\n"
    
    cd "$DEPLOY_DIR"
    
    # Arrêter les anciens conteneurs
    echo -e "${CYAN}🛑 Arrêt des anciens conteneurs...${NC}"
    docker compose -f "$COMPOSE_FILE" down --remove-orphans &>/dev/null || true
    
    # Démarrer les nouveaux
    echo -e "${CYAN}▶️  Démarrage des nouveaux conteneurs...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d &
    spinner $! "Démarrage"
    
    log "INFO" "Services deployed"
}

# ═══════════════════════════════════════════════════════════════
# 🏥 HEALTH CHECKS
# ═══════════════════════════════════════════════════════════════

health_check() {
    echo -e "\n${BLUE}🏥 Vérification de santé des services...${NC}\n"
    
    local max_retries=30
    local retry=0
    
    # Backend health check
    echo -e "${CYAN}Vérification du backend...${NC}"
    while [ $retry -lt $max_retries ]; do
        if curl -s "$HEALTH_URL" | grep -q "ok\|healthy" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Backend: opérationnel"
            break
        fi
        retry=$((retry + 1))
        sleep 2
    done
    
    if [ $retry -eq $max_retries ]; then
        echo -e "${RED}❌ Backend: non accessible après ${max_retries} tentatives${NC}"
        return 1
    fi
    
    # Frontend health check
    retry=0
    echo -e "${CYAN}Vérification du frontend...${NC}"
    while [ $retry -lt $max_retries ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" | grep -q "200\|304" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Frontend: opérationnel"
            break
        fi
        retry=$((retry + 1))
        sleep 2
    done
    
    if [ $retry -eq $max_retries ]; then
        echo -e "${YELLOW}⚠️  Frontend: non accessible (peut prendre plus de temps au premier démarrage)${NC}"
    fi
    
    # Afficher le statut des conteneurs
    echo -e "\n${BLUE}📊 Statut des conteneurs:${NC}\n"
    docker compose -f "$DEPLOY_DIR/$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
}

# ═══════════════════════════════════════════════════════════════
# 🔙 ROLLBACK
# ═══════════════════════════════════════════════════════════════

rollback() {
    echo -e "\n${YELLOW}🔙 Rollback vers la version précédente...${NC}\n"
    
    cd "$DEPLOY_DIR"
    
    # Trouver le dernier backup de commit
    local last_backup=$(ls -t "$BACKUP_DIR"/*_commit.txt 2>/dev/null | head -1)
    
    if [ -z "$last_backup" ]; then
        echo -e "${RED}❌ Aucun backup trouvé pour le rollback${NC}"
        exit 1
    fi
    
    local target_commit=$(cat "$last_backup")
    echo -e "${CYAN}📌 Retour au commit: ${target_commit:0:8}${NC}"
    
    git checkout "$target_commit"
    
    deploy_services
    health_check
    
    log "WARN" "Rollback performed to commit: $target_commit"
}

# ═══════════════════════════════════════════════════════════════
# 📊 STATUS
# ═══════════════════════════════════════════════════════════════

show_status() {
    echo -e "\n${BLUE}📊 Statut de l'application Radar${NC}\n"
    
    cd "$DEPLOY_DIR"
    
    # Git info
    echo -e "${CYAN}📌 Version:${NC}"
    git log -1 --format="   Commit: %h%n   Date: %ci%n   Message: %s" 2>/dev/null || echo "   Non disponible"
    
    echo ""
    
    # Conteneurs
    echo -e "${CYAN}🐳 Conteneurs:${NC}"
    docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "   Non disponible"
    
    echo ""
    
    # Ressources
    echo -e "${CYAN}💻 Ressources:${NC}"
    echo "   CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
    echo "   RAM: $(free -h | awk 'NR==2 {print $3 "/" $2}')"
    echo "   Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2}')"
    
    echo ""
    
    # Backups
    echo -e "${CYAN}💾 Derniers backups:${NC}"
    ls -lh "$BACKUP_DIR"/*_db.sql.gz 2>/dev/null | tail -3 | awk '{print "   " $9 " (" $5 ")"}' || echo "   Aucun backup"
}

# ═══════════════════════════════════════════════════════════════
# 📋 LOGS
# ═══════════════════════════════════════════════════════════════

show_logs() {
    cd "$DEPLOY_DIR"
    docker compose -f "$COMPOSE_FILE" logs -f --tail=100
}

# ═══════════════════════════════════════════════════════════════
# 🎯 MAIN
# ═══════════════════════════════════════════════════════════════

main() {
    banner
    
    local mode="${1:-full}"
    
    case "$mode" in
        --quick|-q)
            echo -e "${CYAN}Mode: Déploiement rapide${NC}"
            check_root
            pre_flight_check
            pull_latest
            deploy_services
            health_check
            ;;
        --full|-f)
            echo -e "${CYAN}Mode: Déploiement complet${NC}"
            check_root
            pre_flight_check
            create_backup
            pull_latest
            build_images
            deploy_services
            run_migrations
            health_check
            ;;
        --rollback|-r)
            check_root
            rollback
            ;;
        --status|-s)
            show_status
            ;;
        --logs|-l)
            show_logs
            ;;
        --backup|-b)
            check_root
            create_backup
            ;;
        --help|-h)
            echo "Usage: $0 [option]"
            echo ""
            echo "Options:"
            echo "  --quick, -q     Déploiement rapide (pull + restart)"
            echo "  --full, -f      Déploiement complet (backup + build + migrations)"
            echo "  --rollback, -r  Retour à la version précédente"
            echo "  --status, -s    Afficher le statut des services"
            echo "  --logs, -l      Afficher les logs en temps réel"
            echo "  --backup, -b    Créer un backup de la base de données"
            echo "  --help, -h      Afficher cette aide"
            ;;
        *)
            echo -e "${RED}Option non reconnue: $mode${NC}"
            echo "Utilisez --help pour voir les options disponibles"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}                    ✅ Opération terminée !                     ${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

main "$@"
