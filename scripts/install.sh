#!/bin/bash

set -e

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

if ! command -v python3 >/dev/null 2>&1; then

    echo "Installing Python..."

    sudo apt update

    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv

fi

if ! command -v rsync >/dev/null 2>&1; then

    echo "Installing rsync..."

    sudo apt update

    sudo apt install -y rsync

fi

if ! command -v docker >/dev/null 2>&1; then

    echo "Installing Docker..."

    sudo apt update

    sudo apt install -y \
        docker.io \
        docker-compose-plugin

    sudo systemctl enable docker

    sudo systemctl start docker

fi

echo ""
echo "Checking Docker service..."

if ! sudo systemctl is-active --quiet docker; then

    sudo systemctl start docker

fi

echo ""
echo "Waiting Docker become ready..."

until sudo docker info >/dev/null 2>&1
do
    sleep 1
done

if ! sudo docker compose version >/dev/null 2>&1; then

    echo ""
    echo "Docker Compose is not available."

    exit 1

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
# Docker Permissions
##################################################

echo ""
echo "Adding current user to docker group..."

sudo usermod -aG docker "$USER" || true

##################################################
# Install systemd service
##################################################

echo ""
echo "Installing systemd service..."

sudo cp \
    systemd/$SERVICE_NAME \
    /etc/systemd/system/

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