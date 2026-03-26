#!/usr/bin/env bash
set -euo pipefail

# Indygestion installer for Unraid hosts
# Usage:
#   ./scripts/install-unraid.sh
# Optional env overrides:
#   MEDIA_ROOT_HOST=/mnt/user/indygestion APP_DIR=/mnt/user/appdata/indygestion ./scripts/install-unraid.sh

APP_DIR="${APP_DIR:-$(pwd)}"
MEDIA_ROOT_HOST="${MEDIA_ROOT_HOST:-/mnt/user/indygestion}"
ENV_FILE="$APP_DIR/.env"
ENV_EXAMPLE="$APP_DIR/.env.example"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] Docker is not installed or not on PATH."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[ERROR] Docker Compose plugin is required (docker compose)."
  exit 1
fi

if [[ ! -f "$ENV_EXAMPLE" ]]; then
  echo "[ERROR] .env.example not found in $APP_DIR"
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[INFO] Creating .env from .env.example"
  cp "$ENV_EXAMPLE" "$ENV_FILE"
fi

echo "[INFO] Creating media directory structure at: $MEDIA_ROOT_HOST"
mkdir -p "$MEDIA_ROOT_HOST"/{projects,staging,archive,_review}

# Update MEDIA_ROOT_HOST in .env (idempotent)
if rg -q '^MEDIA_ROOT_HOST=' "$ENV_FILE"; then
  sed -i "s|^MEDIA_ROOT_HOST=.*|MEDIA_ROOT_HOST=$MEDIA_ROOT_HOST|" "$ENV_FILE"
else
  printf '\nMEDIA_ROOT_HOST=%s\n' "$MEDIA_ROOT_HOST" >> "$ENV_FILE"
fi

# Generate webhook secret if unchanged placeholder remains
if rg -q '^TUSD_WEBHOOK_SECRET=change-this-to-a-long-random-secret$' "$ENV_FILE"; then
  if command -v openssl >/dev/null 2>&1; then
    SECRET="$(openssl rand -hex 32)"
  else
    SECRET="$(date +%s)-indygestion-secret"
  fi
  sed -i "s|^TUSD_WEBHOOK_SECRET=.*|TUSD_WEBHOOK_SECRET=$SECRET|" "$ENV_FILE"
  echo "[INFO] Generated random TUSD_WEBHOOK_SECRET"
fi

cd "$APP_DIR"

echo "[INFO] Validating docker compose"
docker compose config >/dev/null

echo "[INFO] Building and starting Indygestion"
docker compose up -d --build

echo "[INFO] Services status"
docker compose ps

echo "[INFO] Running basic health checks"
curl -fsS http://localhost:8000/health >/dev/null && echo "  - backend: OK"
curl -fsS http://localhost:9000/health >/dev/null && echo "  - whisper: OK"
curl -fsSI http://localhost:1080/files/ >/dev/null && echo "  - tusd: OK"

echo
echo "Indygestion installed."
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000/api/v1"
echo "Uploads:  http://localhost:1080/files"
