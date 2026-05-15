#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/opc/coupax-homepage/board"
SERVICE_NAME="board"

sudo dnf -y update
sudo dnf -y install python3 python3-pip python3-devel gcc nginx

cd "$APP_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "[INFO] .env file created. Edit it before production use."
fi

sudo cp deploy/${SERVICE_NAME}.service /etc/systemd/system/${SERVICE_NAME}.service
sudo systemctl daemon-reload
sudo systemctl enable --now ${SERVICE_NAME}

sudo cp deploy/nginx-board.conf /etc/nginx/conf.d/board.conf
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl restart nginx

echo "[DONE] board service + nginx are running."
