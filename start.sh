#!/bin/bash

# LOKAHOME API - Script de démarrage
# Usage: ./start.sh [command]
#
# Commands:
#   dev       - Démarrer en mode développement (défaut)
#   docker    - Démarrer avec Docker Compose
#   test      - Lancer les tests
#   migrate   - Appliquer les migrations
#   shell     - Ouvrir un shell Python
#   celery    - Démarrer les workers Celery
#   lint      - Vérifier le code (format + lint)
#   format    - Formater le code
#   help      - Afficher l'aide

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Vérifier si .env existe, sinon le créer
check_env() {
    if [ ! -f .env ]; then
        warning "Fichier .env non trouvé"
        if [ -f .env.example ]; then
            cp .env.example .env
            success "Fichier .env créé à partir de .env.example"
            warning "Pensez à configurer vos variables d'environnement dans .env"
        else
            error "Fichier .env.example non trouvé"
        fi
    fi
}

# Vérifier les dépendances système
check_dependencies() {
    if ! command -v python3 &> /dev/null; then
        error "Python 3 n'est pas installé"
    fi

    if ! command -v pip &> /dev/null; then
        error "pip n'est pas installé"
    fi
}

# Installer les dépendances Python
install_deps() {
    info "Installation des dépendances..."
    pip install -r requirements.txt -q
    success "Dépendances installées"
}

# Activer l'environnement virtuel si présent
activate_venv() {
    if [ -d "venv" ]; then
        source venv/bin/activate
        return 0
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
        return 0
    fi
    return 1
}

# Créer l'environnement virtuel
create_venv() {
    info "Création de l'environnement virtuel..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    success "Environnement virtuel créé"
}

# Mode développement
cmd_dev() {
    check_env
    check_dependencies

    # Activer ou créer venv automatiquement
    if ! activate_venv; then
        warning "Environnement virtuel non trouvé, création automatique..."
        create_venv
        install_deps
    fi

    # Vérifier si uvicorn est installé, sinon installer les dépendances
    if ! python -c "import uvicorn" &> /dev/null; then
        warning "uvicorn n'est pas installé, installation des dépendances..."
        install_deps
    fi

    info "Démarrage en mode développement..."
    echo ""
    echo -e "${GREEN}API disponible sur: http://localhost:8000${NC}"
    echo -e "${GREEN}Documentation: http://localhost:8000/docs${NC}"
    echo ""

    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

# Mode Docker
cmd_docker() {
    # Vérifier docker compose (nouvelle syntaxe) ou docker-compose
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        error "Docker Compose n'est pas installé"
    fi

    info "Démarrage avec Docker Compose..."
    $DOCKER_COMPOSE up -d

    success "Services démarrés"
    echo ""
    echo -e "${GREEN}API disponible sur: http://localhost:8000${NC}"
    echo -e "${GREEN}Documentation: http://localhost:8000/docs${NC}"
    echo ""
    echo "Commandes utiles:"
    echo "  $DOCKER_COMPOSE logs -f api    # Voir les logs"
    echo "  $DOCKER_COMPOSE down           # Arrêter les services"
}

# Arrêter Docker
cmd_docker_down() {
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        error "Docker Compose n'est pas installé"
    fi

    info "Arrêt des services Docker..."
    $DOCKER_COMPOSE down
    success "Services arrêtés"
}

# Lancer les tests
cmd_test() {
    check_env
    activate_venv
    info "Lancement des tests..."
    pytest -v --cov=app "$@"
}

# Appliquer les migrations
cmd_migrate() {
    check_env
    activate_venv
    info "Application des migrations..."
    alembic upgrade head
    success "Migrations appliquées"
}

# Créer une nouvelle migration
cmd_makemigrations() {
    check_env
    activate_venv
    if [ -z "$1" ]; then
        error "Usage: ./start.sh makemigrations \"description\""
    fi
    info "Création de la migration: $1"
    alembic revision --autogenerate -m "$1"
    success "Migration créée"
}

# Shell Python interactif
cmd_shell() {
    check_env
    activate_venv
    info "Ouverture du shell Python..."
    python3 -c "
from app.core.config import settings
from app.core.database import Base
print('LOKAHOME Shell')
print('Variables disponibles: settings, Base')
print('')
"
    python3 -i -c "from app.core.config import settings; from app.core.database import Base"
}

# Démarrer Celery
cmd_celery() {
    check_env
    activate_venv
    info "Démarrage des workers Celery..."
    celery -A app.tasks worker --loglevel=info
}

# Démarrer Celery Beat (scheduler)
cmd_celery_beat() {
    check_env
    activate_venv
    info "Démarrage de Celery Beat..."
    celery -A app.tasks beat --loglevel=info
}

# Vérifier le code
cmd_lint() {
    activate_venv
    info "Vérification du code..."
    echo ""

    info "Running ruff..."
    ruff check app || true

    info "Running mypy..."
    mypy app || true

    success "Vérification terminée"
}

# Formater le code
cmd_format() {
    activate_venv
    info "Formatage du code..."

    info "Running black..."
    black app tests

    info "Running isort..."
    isort app tests

    success "Code formaté"
}

# Installation complète
cmd_install() {
    check_dependencies
    check_env

    # Créer venv si nécessaire
    if ! activate_venv; then
        create_venv
    else
        info "Environnement virtuel existant activé"
    fi

    install_deps

    success "Installation terminée"
    echo ""
    echo "Prochaines étapes:"
    echo "  1. Configurer .env avec vos paramètres"
    echo "  2. Démarrer PostgreSQL et Redis (ou: ./start.sh docker)"
    echo "  3. Lancer: ./start.sh migrate"
    echo "  4. Lancer: ./start.sh dev"
}

# Afficher l'aide
cmd_help() {
    echo ""
    echo -e "${BLUE}LOKAHOME API - Script de démarrage${NC}"
    echo ""
    echo "Usage: ./start.sh [command]"
    echo ""
    echo "Commands:"
    echo "  dev              Démarrer en mode développement (défaut)"
    echo "  docker           Démarrer avec Docker Compose"
    echo "  docker-down      Arrêter les services Docker"
    echo "  install          Installation complète (venv + deps)"
    echo "  test             Lancer les tests"
    echo "  migrate          Appliquer les migrations"
    echo "  makemigrations   Créer une nouvelle migration"
    echo "  shell            Ouvrir un shell Python"
    echo "  celery           Démarrer les workers Celery"
    echo "  celery-beat      Démarrer Celery Beat (scheduler)"
    echo "  lint             Vérifier le code (ruff + mypy)"
    echo "  format           Formater le code (black + isort)"
    echo "  help             Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  ./start.sh                           # Démarrer en dev"
    echo "  ./start.sh install                   # Première installation"
    echo "  ./start.sh docker                    # Démarrer avec Docker"
    echo "  ./start.sh docker-down               # Arrêter Docker"
    echo "  ./start.sh test -k test_login        # Tester un pattern"
    echo "  ./start.sh makemigrations \"add users table\""
    echo ""
}

# Point d'entrée principal
main() {
    cd "$(dirname "$0")"

    case "${1:-dev}" in
        dev)
            cmd_dev
            ;;
        docker)
            cmd_docker
            ;;
        docker-down)
            cmd_docker_down
            ;;
        install)
            cmd_install
            ;;
        test)
            shift
            cmd_test "$@"
            ;;
        migrate)
            cmd_migrate
            ;;
        makemigrations)
            shift
            cmd_makemigrations "$@"
            ;;
        shell)
            cmd_shell
            ;;
        celery)
            cmd_celery
            ;;
        celery-beat)
            cmd_celery_beat
            ;;
        lint)
            cmd_lint
            ;;
        format)
            cmd_format
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            error "Commande inconnue: $1 (utilisez './start.sh help' pour l'aide)"
            ;;
    esac
}

main "$@"
