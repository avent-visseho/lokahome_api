#!/bin/bash
# ===========================================
# LOKAHOME - Script de setup initial du serveur
# À exécuter UNE SEULE FOIS sur le VPS
# ===========================================
set -euo pipefail

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Vérifier qu'on est root
if [ "$EUID" -ne 0 ]; then
    error "Ce script doit être exécuté en tant que root"
fi

echo "============================================"
echo "  LOKAHOME - Setup Serveur de Production"
echo "============================================"
echo ""

# 1. Mise à jour du système
info "Mise à jour du système..."
apt-get update -qq && apt-get upgrade -y -qq
ok "Système mis à jour"

# 2. Installer les paquets essentiels
info "Installation des paquets essentiels..."
apt-get install -y -qq \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    ufw \
    fail2ban \
    htop \
    unzip \
    software-properties-common
ok "Paquets installés"

# 3. Installer Docker
if ! command -v docker &> /dev/null; then
    info "Installation de Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    ok "Docker installé"
else
    ok "Docker déjà installé"
fi

# 4. Installer Docker Compose plugin
if ! docker compose version &> /dev/null; then
    info "Installation de Docker Compose..."
    apt-get install -y -qq docker-compose-plugin
    ok "Docker Compose installé"
else
    ok "Docker Compose déjà installé"
fi

# 5. Créer un utilisateur deploy
if ! id "deploy" &>/dev/null; then
    info "Création de l'utilisateur deploy..."
    adduser --disabled-password --gecos "" deploy
    usermod -aG docker deploy
    mkdir -p /home/deploy/.ssh
    cp /root/.ssh/authorized_keys /home/deploy/.ssh/ 2>/dev/null || true
    chown -R deploy:deploy /home/deploy/.ssh
    chmod 700 /home/deploy/.ssh
    ok "Utilisateur deploy créé et ajouté au groupe docker"
else
    usermod -aG docker deploy
    ok "Utilisateur deploy existe déjà"
fi

# 6. Configurer le firewall
info "Configuration du firewall (UFW)..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable
ok "Firewall configuré (SSH, HTTP, HTTPS)"

# 7. Configurer fail2ban
info "Configuration de fail2ban..."
cat > /etc/fail2ban/jail.local << 'JAIL'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
maxretry = 3
JAIL
systemctl enable fail2ban
systemctl restart fail2ban
ok "fail2ban configuré"

# 8. Optimiser le système
info "Optimisation système..."
cat > /etc/sysctl.d/99-lokahome.conf << 'SYSCTL'
# Optimisations réseau
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
net.core.netdev_max_backlog = 65535

# Mémoire
vm.overcommit_memory = 1
vm.swappiness = 10

# Fichiers ouverts
fs.file-max = 2097152
SYSCTL
sysctl -p /etc/sysctl.d/99-lokahome.conf > /dev/null 2>&1
ok "Optimisations système appliquées"

# 9. Configurer les limites système
cat > /etc/security/limits.d/lokahome.conf << 'LIMITS'
* soft nofile 65535
* hard nofile 65535
* soft nproc 65535
* hard nproc 65535
LIMITS

# 10. Créer la structure du projet
info "Création de la structure du projet..."
mkdir -p /opt/lokahome
chown deploy:deploy /opt/lokahome
ok "Structure créée dans /opt/lokahome"

# 11. Configurer la rotation des logs Docker
cat > /etc/docker/daemon.json << 'DOCKER'
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "storage-driver": "overlay2"
}
DOCKER
systemctl restart docker
ok "Rotation des logs Docker configurée"

# 12. Configurer le swap (si pas de swap)
if [ "$(swapon --show | wc -l)" -eq 0 ]; then
    info "Configuration du swap (2GB)..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    ok "Swap de 2GB configuré"
else
    ok "Swap déjà configuré"
fi

echo ""
echo "============================================"
echo -e "${GREEN}  Setup terminé avec succès !${NC}"
echo "============================================"
echo ""
echo "Prochaines étapes :"
echo "  1. Depuis votre machine locale, lancez : ./scripts/deploy.sh"
echo "  2. L'application sera accessible sur http://185.194.217.12"
echo ""
echo "Informations :"
echo "  - Utilisateur deploy : deploy (groupe docker)"
echo "  - Projet : /opt/lokahome"
echo "  - Firewall : SSH(22), HTTP(80), HTTPS(443)"
echo "  - fail2ban : activé (3 tentatives SSH max)"
echo ""
