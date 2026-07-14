#!/bin/bash

set -euo pipefail

PROJECT_NAME="service-monitoring"
INSTALL_DIR="/opt/$PROJECT_NAME"
SERVICE_NAME="$PROJECT_NAME.service"

echo "========================================="
echo "Installing Service Monitoring Host"
echo "========================================="

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo ""
echo "Project directory:"
echo "$PROJECT_DIR"

##################################################
# Install prerequisites
##################################################

echo ""
echo "Checking prerequisites..."

sudo apt update

if ! command -v python3 >/dev/null 2>&1; then
    echo "Installing Python..."

    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv
fi

if ! command -v rsync >/dev/null 2>&1; then
    echo "Installing rsync..."

    sudo apt install -y rsync
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "Installing Docker..."

    sudo apt install -y docker.io docker-compose-v2
fi

##################################################
# Prepare Docker
##################################################

echo ""
echo "Preparing Docker..."

# Kill manually started daemon (safe if not running)
sudo pkill -f dockerd || true

# Remove stale PID
sudo rm -f /var/run/docker.pid

# Reset failed state
sudo systemctl reset-failed docker || true

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable containerd
sudo systemctl enable docker

# Restart services
sudo systemctl restart containerd
sudo systemctl restart docker

##################################################
# Wait Docker
##################################################

echo ""
echo "Waiting Docker become ready..."

timeout=30

until sudo docker info >/dev/null 2>&1
do
    sleep 1
    timeout=$((timeout-1))

    if [ "$timeout" -le 0 ]; then
        echo ""
        echo "Docker failed to start."

        echo ""
        sudo systemctl status docker --no-pager

        echo ""
        sudo journalctl -u docker -n 100 --no-pager

        exit 1
    fi
done

##################################################
# Validate Docker Compose
##################################################

if ! sudo docker compose version >/dev/null 2>&1; then

    echo ""
    echo "Docker Compose is not available."

    exit 1

fi

##################################################
# Docker permissions
##################################################

echo ""
echo "Adding current user to docker group..."

sudo usermod -aG docker "$USER" || true

##################################################
# Create installation folder
##################################################

echo ""
echo "Creating installation directory..."

sudo rm -rf "$INSTALL_DIR"

sudo mkdir -p "$INSTALL_DIR"

##################################################
# Copy project
##################################################

echo ""
echo "Copying project..."

sudo rsync -a \
    --exclude ".git" \
    --exclude ".venv" \
    --exclude "__pycache__" \
    --exclude "*.pyc" \
    "$PROJECT_DIR"/ \
    "$INSTALL_DIR"/

sudo chown -R "$USER:$USER" "$INSTALL_DIR"

##################################################
# Python Virtual Environment
##################################################

cd "$INSTALL_DIR"

echo ""
echo "Creating virtual environment..."

python3 -m venv .venv

echo ""
echo "Activating virtual environment..."

source .venv/bin/activate

echo ""
echo "Updating pip..."

pip install --upgrade pip

echo ""
echo "Installing Python dependencies..."

pip install -r requirements.txt

##################################################
# Deploy containers
##################################################

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yaml}"

if [ -f "$COMPOSE_FILE" ]; then

    echo ""
    echo "Deploying containers from $COMPOSE_FILE..."

    python scripts/ports_check.py -f "$COMPOSE_FILE" --fix-cdi || {
        echo ""
        echo "WARNING: Container deploy failed."
        echo "Run manually later:"
        echo "  cd $INSTALL_DIR && python scripts/ports_check.py -f $COMPOSE_FILE"
    }

else

    echo ""
    echo "WARNING: Compose file '$COMPOSE_FILE' not found."
    echo "Skipping container deployment."
    echo "Run manually when ready:"
    echo "  cd $INSTALL_DIR && python scripts/ports_check.py -f <compose-file>"

fi

##################################################
# Install systemd service
##################################################

echo ""
echo "Installing systemd service..."

sudo cp \
    "systemd/$SERVICE_NAME" \
    "/etc/systemd/system/"

sudo systemctl daemon-reload

sudo systemctl enable "$PROJECT_NAME"

sudo systemctl restart "$PROJECT_NAME"

##################################################
# Validate installation
##################################################

echo ""
echo "Waiting service startup..."

sleep 5

if sudo systemctl is-active --quiet "$PROJECT_NAME"; then

    echo ""
    echo "Service started successfully."

else

    echo ""
    echo "Service failed to start."

    sudo journalctl -u "$PROJECT_NAME" -n 50 --no-pager

    exit 1

fi

##################################################
# Installation Summary
##################################################

echo ""
echo "========================================="
echo "Installation completed successfully!"
echo "========================================="

echo ""
echo "Python version:"
python3 --version

echo ""
echo "Docker version:"
sudo docker --version

echo ""
echo "Docker Compose version:"
sudo docker compose version

echo ""
echo "Service status:"
sudo systemctl status "$PROJECT_NAME" --no-pager

echo ""
echo "Useful commands:"
echo "-----------------------------------------"
echo "View logs:"
echo "sudo journalctl -u $PROJECT_NAME -f"

echo ""
echo "Restart service:"
echo "sudo systemctl restart $PROJECT_NAME"

echo ""
echo "Stop service:"
echo "sudo systemctl stop $PROJECT_NAME"

echo ""
echo "Docker containers:"
echo "docker ps"

echo ""
echo "NOTE:"
echo "If this is the first Docker installation,"
echo "logout/login (or run 'newgrp docker')"
echo "to use Docker without sudo."