#!/bin/bash

set -e

echo "========================================="
echo "Installing Service Monitoring Host"
echo "========================================="

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_DIR"

echo "Creating virtual environment..."

python3 -m venv .venv

echo "Activating environment..."

source .venv/bin/activate

echo "Installing dependencies..."

pip install --upgrade pip

pip install -r requirements.txt

echo "Installing systemd service..."

sudo cp systemd/service-monitoring.service \
/etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable service-monitoring

sudo systemctl start service-monitoring

echo ""
echo "Installation completed."