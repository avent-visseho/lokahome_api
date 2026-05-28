#!/bin/bash
# ===========================================
# LOKAHOME - Script de déploiement
# Usage: ./scripts/deploy.sh [setup|deploy|ssl|logs|status|rollback|db-migrate]
# ===========================================
set -euo pipefail

# ---- Configuration ----
SERVER_IP="185.194.217.12"
SERVER_USER="root"
REMOTE_DIR="/opt/lokahome"
PROJECT_NAME="lokahome"
COMPOSE_FILE="docker-compose.prod.yml"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
header() { echo -e "\n${CYAN}=== $1 ===${NC}\n"; }

SSH_CMD="ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP}"
SCP_CMD="scp -o StrictHostKeyChecking=no"

# ---- Fonctions ----

show_help() {
    echo ""
    echo "Usage: ./scripts/deploy.sh <commande>"
    echo ""
    echo "Commandes disponibles :"
    echo "  setup        - Setup initial du serveur (1ère fois uniquement)"
    echo "  deploy       - Déployer / mettre à jour l'application"
    echo "  ssl DOMAIN   - Installer le certificat SSL (ex: ssl api.lokahome.bj)"
    echo "  logs         - Voir les logs en temps réel"
    echo "  status       - Voir le statut des services"
    echo "  rollback     - Revenir à la version précédente"
    echo "  db-migrate   - Exécuter les migrations Alembic"
    echo "  restart      - Redémarrer tous les services"
    echo "  shell        - Ouvrir un shell sur le serveur"
    echo ""
}

# Setup initial du serveur
do_setup() {
    header "Setup initial du serveur ${SERVER_IP}"

    info "Envoi du script de setup..."
    ${SCP_CMD} scripts/server-setup.sh ${SERVER_USER}@${SERVER_IP}:/tmp/server-setup.sh

    info "Exécution du setup sur le serveur..."
    ${SSH_CMD} "chmod +x /tmp/server-setup.sh && /tmp/server-setup.sh"

    ok "Setup du serveur terminé !"
}

# Déploiement principal
do_deploy() {
    header "Déploiement sur ${SERVER_IP}"

    # Vérifier que .env.production existe et est configuré
    if [ ! -f ".env.production" ]; then
        error "Fichier .env.production manquant. Copiez .env.production.example et configurez-le."
    fi

    if grep -q "CHANGE_ME" .env.production; then
        error "Des valeurs CHANGE_ME trouvées dans .env.production. Configurez toutes les variables."
    fi

    # Créer le répertoire distant
    info "Préparation du serveur..."
    ${SSH_CMD} "mkdir -p ${REMOTE_DIR}"

    # Synchroniser les fichiers (exclure venv, __pycache__, .git, etc.)
    info "Synchronisation des fichiers..."
    rsync -avz --progress \
        --exclude '.git' \
        --exclude '.gitignore' \
        --exclude 'venv' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.pytest_cache' \
        --exclude '.mypy_cache' \
        --exclude '.ruff_cache' \
        --exclude 'tests' \
        --exclude '.env' \
        --exclude 'htmlcov' \
        --exclude '.coverage' \
        --exclude 'CLAUDE.md' \
        -e "ssh -o StrictHostKeyChecking=no" \
        ./ ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/
    ok "Fichiers synchronisés"

    # Extraire DB_PASSWORD du .env.production pour docker-compose
    DB_PASSWORD=$(grep "^DATABASE_URL" .env.production | sed 's/.*:\/\/lokahome:\(.*\)@.*/\1/')

    # Construire et démarrer les conteneurs
    info "Construction et démarrage des conteneurs..."
    ${SSH_CMD} "cd ${REMOTE_DIR} && \
        export DB_PASSWORD='${DB_PASSWORD}' && \
        docker compose -f ${COMPOSE_FILE} build --no-cache && \
        docker compose -f ${COMPOSE_FILE} up -d"
    ok "Conteneurs démarrés"

    # Attendre que l'API soit prête
    info "Attente du démarrage de l'API..."
    for i in $(seq 1 30); do
        if ${SSH_CMD} "curl -sf http://localhost:8080/health > /dev/null 2>&1"; then
            ok "API opérationnelle !"
            break
        fi
        if [ "$i" -eq 30 ]; then
            warn "L'API n'a pas répondu dans les 30 secondes. Vérifiez les logs."
            ${SSH_CMD} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} logs --tail=20 api"
        fi
        sleep 2
    done

    # Exécuter les migrations
    info "Exécution des migrations..."
    ${SSH_CMD} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} exec -T api alembic upgrade head" || \
        warn "Pas de migrations à appliquer ou erreur (vérifiez les logs)"

    # Nettoyage des anciennes images Docker
    info "Nettoyage des images Docker inutilisées..."
    ${SSH_CMD} "docker image prune -f" > /dev/null 2>&1

    echo ""
    ok "Déploiement terminé avec succès !"
    echo ""
    echo -e "  ${GREEN}API accessible sur :${NC} http://${SERVER_IP}"
    echo -e "  ${GREEN}Documentation :${NC}    http://${SERVER_IP}/docs"
    echo -e "  ${GREEN}Health check :${NC}     http://${SERVER_IP}/health"
    echo ""
}

# Installer SSL
do_ssl() {
    local DOMAIN="${1:-}"
    if [ -z "$DOMAIN" ]; then
        error "Usage: ./scripts/deploy.sh ssl <domaine> (ex: ssl api.lokahome.bj)"
    fi

    header "Installation SSL pour ${DOMAIN}"

    info "Obtention du certificat Let's Encrypt..."
    ${SSH_CMD} "cd ${REMOTE_DIR} && \
        docker compose -f ${COMPOSE_FILE} run --rm certbot certonly \
            --webroot \
            --webroot-path=/var/www/certbot \
            --email admin@lokahome.bj \
            --agree-tos \
            --no-eff-email \
            -d ${DOMAIN}"

    info "Activation de la configuration HTTPS dans nginx..."
    # Décommenter le bloc HTTPS et le redirect
    ${SSH_CMD} "cd ${REMOTE_DIR} && \
        sed -i 's|# server_name api.lokahome.bj;|server_name ${DOMAIN};|g' nginx/conf.d/default.conf && \
        sed -i 's|server_name _;|server_name ${DOMAIN};|g' nginx/conf.d/default.conf && \
        sed -i 's|api.lokahome.bj|${DOMAIN}|g' nginx/conf.d/default.conf"

    info "Redémarrage de nginx..."
    ${SSH_CMD} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} restart nginx"

    ok "SSL configuré pour ${DOMAIN}"
    echo ""
    echo "IMPORTANT: Décommentez manuellement le bloc HTTPS dans nginx/conf.d/default.conf"
    echo "puis redéployez avec: ./scripts/deploy.sh deploy"
}

# Voir les logs
do_logs() {
    local SERVICE="${1:-}"
    header "Logs en temps réel"

    if [ -n "$SERVICE" ]; then
        ${SSH_CMD} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} logs -f --tail=100 ${SERVICE}"
    else
        ${SSH_CMD} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} logs -f --tail=100"
    fi
}

# Statut des services
do_status() {
    header "Statut des services"
    ${SSH_CMD} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} ps"
    echo ""
    info "Utilisation des ressources :"
    ${SSH_CMD} "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}' | grep lokahome || true"
    echo ""
    info "Espace disque Docker :"
    ${SSH_CMD} "docker system df"
}

# Rollback
do_rollback() {
    header "Rollback vers la version précédente"
    warn "Cette action va redémarrer les conteneurs avec les images précédentes."
    read -p "Continuer ? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${SSH_CMD} "cd ${REMOTE_DIR} && \
            docker compose -f ${COMPOSE_FILE} down && \
            docker compose -f ${COMPOSE_FILE} up -d"
        ok "Rollback effectué"
    fi
}

# Migrations base de données
do_db_migrate() {
    header "Migrations de la base de données"
    local ACTION="${1:-upgrade}"

    if [ "$ACTION" = "upgrade" ]; then
        info "Application des migrations..."
        ${SSH_CMD} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} exec -T api alembic upgrade head"
    elif [ "$ACTION" = "downgrade" ]; then
        info "Rollback de la dernière migration..."
        ${SSH_CMD} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} exec -T api alembic downgrade -1"
    elif [ "$ACTION" = "history" ]; then
        info "Historique des migrations..."
        ${SSH_CMD} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} exec -T api alembic history"
    else
        error "Usage: ./scripts/deploy.sh db-migrate [upgrade|downgrade|history]"
    fi
    ok "Opération terminée"
}

# Redémarrage
do_restart() {
    header "Redémarrage des services"
    local SERVICE="${1:-}"

    if [ -n "$SERVICE" ]; then
        info "Redémarrage de ${SERVICE}..."
        ${SSH_CMD} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} restart ${SERVICE}"
    else
        info "Redémarrage de tous les services..."
        ${SSH_CMD} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} restart"
    fi
    ok "Redémarrage effectué"
}

# Shell sur le serveur
do_shell() {
    ${SSH_CMD}
}

# ---- Main ----
COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    setup)      do_setup "$@" ;;
    deploy)     do_deploy "$@" ;;
    ssl)        do_ssl "$@" ;;
    logs)       do_logs "$@" ;;
    status)     do_status "$@" ;;
    rollback)   do_rollback "$@" ;;
    db-migrate) do_db_migrate "$@" ;;
    restart)    do_restart "$@" ;;
    shell)      do_shell "$@" ;;
    help|*)     show_help ;;
esac
