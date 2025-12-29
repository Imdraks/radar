#!/bin/bash
#
# 📊 RADAR - Script de Monitoring
# ================================
# Collecte et affiche les métriques de l'application
#

set -e

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/radar}"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              📊 RADAR - Tableau de Bord en Direct             ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

while true; do
    # Clear and redraw
    tput cup 4 0
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}🕐 $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # System resources
    echo -e "${BLUE}💻 Ressources Système:${NC}"
    echo -e "   CPU:     $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
    echo -e "   RAM:     $(free -h | awk 'NR==2 {print $3 "/" $2}')"
    echo -e "   Disk:    $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 " used)"}')"
    echo -e "   Load:    $(uptime | awk -F'load average:' '{print $2}')"
    echo ""
    
    # Docker containers
    echo -e "${BLUE}🐳 Conteneurs Docker:${NC}"
    docker compose -f "$DEPLOY_DIR/$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | while read line; do
        if echo "$line" | grep -q "Up"; then
            echo -e "   ${GREEN}●${NC} $line"
        elif echo "$line" | grep -q "NAME"; then
            echo -e "   $line"
        else
            echo -e "   ${RED}●${NC} $line"
        fi
    done
    echo ""
    
    # API Health
    echo -e "${BLUE}🏥 Santé des Services:${NC}"
    
    # Backend
    backend_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
    if [ "$backend_status" = "200" ]; then
        echo -e "   ${GREEN}✓${NC} Backend API: OK (HTTP $backend_status)"
    else
        echo -e "   ${RED}✗${NC} Backend API: DOWN (HTTP $backend_status)"
    fi
    
    # Frontend
    frontend_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")
    if [ "$frontend_status" = "200" ] || [ "$frontend_status" = "304" ]; then
        echo -e "   ${GREEN}✓${NC} Frontend: OK (HTTP $frontend_status)"
    else
        echo -e "   ${YELLOW}○${NC} Frontend: N/A (HTTP $frontend_status)"
    fi
    
    # PostgreSQL
    pg_status=$(docker compose -f "$DEPLOY_DIR/$COMPOSE_FILE" exec -T postgres pg_isready -U radar 2>/dev/null && echo "OK" || echo "DOWN")
    if [ "$pg_status" = "OK" ]; then
        echo -e "   ${GREEN}✓${NC} PostgreSQL: OK"
    else
        echo -e "   ${RED}✗${NC} PostgreSQL: DOWN"
    fi
    
    # Redis
    redis_status=$(docker compose -f "$DEPLOY_DIR/$COMPOSE_FILE" exec -T redis redis-cli ping 2>/dev/null || echo "DOWN")
    if [ "$redis_status" = "PONG" ]; then
        echo -e "   ${GREEN}✓${NC} Redis: OK"
    else
        echo -e "   ${RED}✗${NC} Redis: DOWN"
    fi
    echo ""
    
    # Recent logs (last 5 errors)
    echo -e "${BLUE}📋 Dernières Erreurs:${NC}"
    docker compose -f "$DEPLOY_DIR/$COMPOSE_FILE" logs --tail=100 2>/dev/null | grep -i "error\|exception\|failed" | tail -3 | while read line; do
        echo -e "   ${RED}!${NC} $(echo $line | cut -c1-70)..."
    done
    echo ""
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "   Appuyez sur ${YELLOW}Ctrl+C${NC} pour quitter | Rafraîchissement: 5s"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    sleep 5
done
