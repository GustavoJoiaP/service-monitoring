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
# Detect container runtime
##################################################

USE_PODMAN=false

if command -v podman >/dev/null 2>&1; then
    echo "Podman detected."
    USE_PODMAN=true
elif command -v docker >/dev/null 2>&1; then
    echo "Docker detected."
else
    echo "No container runtime found. Installing Podman..."

    sudo apt update
    sudo apt install -y podman podman-compose

    USE_PODMAN=true
fi

RUNTIME_BIN="docker"
RUNTIME_COMPOSE="docker compose"
RUNTIME_SERVICE="docker.service"

if [ "$USE_PODMAN" = true ]; then
    RUNTIME_BIN="podman"
    RUNTIME_SERVICE="podman.socket"

    if podman compose version >/dev/null 2>&1; then
        RUNTIME_COMPOSE="podman compose"
    else
        RUNTIME_COMPOSE="podman-compose"
    fi
fi

echo "Using runtime: $RUNTIME_BIN"
echo "Using compose: $RUNTIME_COMPOSE"

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

##################################################
# Prepare container runtime
##################################################

echo ""
echo "Preparing $RUNTIME_BIN..."

if [ "$USE_PODMAN" = true ]; then
    sudo systemctl enable podman.socket 2>/dev/null || true
    sudo systemctl start podman.socket 2>/dev/null || true
else
    sudo pkill -f dockerd || true
    sudo rm -f /var/run/docker.pid
    sudo systemctl reset-failed docker || true
    sudo systemctl daemon-reload
    sudo systemctl enable containerd
    sudo systemctl enable docker
    sudo systemctl restart containerd
    sudo systemctl restart docker
fi

##################################################
# Wait for runtime
##################################################

echo ""
echo "Waiting $RUNTIME_BIN become ready..."

timeout=30

until $RUNTIME_BIN info >/dev/null 2>&1
do
    sleep 1
    timeout=$((timeout-1))

    if [ "$timeout" -le 0 ]; then
        echo ""
        echo "$RUNTIME_BIN failed to start."
        exit 1
    fi
done

##################################################
# Validate Compose
##################################################

echo ""
echo "Validating compose..."

if ! $RUNTIME_COMPOSE version >/dev/null 2>&1; then
    echo ""
    echo "$RUNTIME_COMPOSE is not available."
    exit 1
fi

##################################################
# Permissions (Docker only)
##################################################

if [ "$USE_PODMAN" = false ]; then
    echo ""
    echo "Adding current user to docker group..."
    sudo usermod -aG docker "$USER" || true
fi

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

COMPOSE_FILE="${COMPOSE_FILE:-podman-compose.yaml}"

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
echo "$RUNTIME_BIN version:"
$RUNTIME_BIN --version

echo ""
echo "Compose version:"
$RUNTIME_COMPOSE version

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
echo "Containers:"
echo "$RUNTIME_BIN ps"

if [ "$USE_PODMAN" = false ]; then
    echo ""
    echo "NOTE:"
    echo "If this is the first Docker installation,"
    echo "logout/login (or run 'newgrp docker')"
    echo "to use Docker without sudo."
fi
