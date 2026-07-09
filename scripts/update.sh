#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_DIR"

git pull

source .venv/bin/activate

pip install -r requirements.txt

sudo systemctl restart service-monitoring

echo "Updated successfully."