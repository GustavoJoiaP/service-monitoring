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

echo ""
echo "Creating installation directory..."

sudo rm -rf "$INSTALL_DIR"

sudo mkdir -p "$INSTALL_DIR"

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

cd "$INSTALL_DIR"

echo ""
echo "Creating virtual environment..."

python3 -m venv .venv

echo ""
echo "Activating environment..."

source .venv/bin/activate

echo ""
echo "Installing dependencies..."

pip install --upgrade pip

pip install -r requirements.txt

echo ""
echo "Installing systemd service..."

sudo cp systemd/$SERVICE_NAME \
    /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable $PROJECT_NAME

sudo systemctl restart $PROJECT_NAME

echo ""
echo "========================================="
echo "Installation completed successfully!"
echo "========================================="

echo ""

systemctl status $PROJECT_NAME --no-pager