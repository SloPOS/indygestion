#!/usr/bin/env bash
set -euo pipefail

# Indygestion bootstrap installer for Unraid/Linux
# - Downloads app source (git clone or tarball)
# - Prepares .env and media paths
# - Runs docker compose up -d --build
#
# Usage:
#   bash <(curl -fsSL https://raw.githubusercontent.com/SloPOS/indygestion/main/scripts/bootstrap-unraid.sh)
#
# Optional env overrides:
#   REPO_URL=https://github.com/SloPOS/indygestion.git
#   REPO_BRANCH=main
#   INSTALL_DIR=/mnt/user/appdata/indygestion
#   MEDIA_ROOT_HOST=/mnt/user/indygestion
#   POSTGRES_PASSWORD=...
#   TUSD_WEBHOOK_SECRET=...
#   AUTO_START=true|false

REPO_URL="${REPO_URL:-https://github.com/SloPOS/indygestion.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/mnt/user/appdata/indygestion}"
MEDIA_ROOT_HOST="${MEDIA_ROOT_HOST:-/mnt/user/indygestion}"
AUTO_START="${AUTO_START:-true}"

log() { printf '\033[1;34m[indygestion]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    err "Missing required command: $1"
    return 1
  }
}

gen_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    date +%s%N | sha256sum | awk '{print $1}'
  fi
}

ensure_dependencies() {
  require_cmd bash
  require_cmd sed
  require_cmd awk
  require_cmd grep
  require_cmd curl
  require_cmd docker

  if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
    warn "Using legacy docker-compose binary."
  else
    err "Neither 'docker compose' nor 'docker-compose' is available."
    err "Install Docker Compose plugin on Unraid (recommended) and retry."
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    err "Docker daemon is not reachable. Is Docker enabled in Unraid settings?"
    exit 1
  fi
}

download_repo() {
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    log "Existing git repo found at $INSTALL_DIR — updating."
    git -C "$INSTALL_DIR" fetch origin "$REPO_BRANCH"
    git -C "$INSTALL_DIR" checkout "$REPO_BRANCH"
    git -C "$INSTALL_DIR" pull --ff-only origin "$REPO_BRANCH"
    return
  fi

  mkdir -p "$INSTALL_DIR"

  if command -v git >/dev/null 2>&1; then
    log "Cloning repository: $REPO_URL (branch: $REPO_BRANCH)"
    rm -rf "$INSTALL_DIR"
    git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$INSTALL_DIR"
    return
  fi

  warn "git not found; falling back to GitHub tarball download."
  require_cmd tar

  local tmp_tar
  tmp_tar="$(mktemp /tmp/indygestion.XXXXXX.tar.gz)"
  local tar_url
  tar_url="${REPO_URL%.git}/archive/refs/heads/${REPO_BRANCH}.tar.gz"

  log "Downloading source tarball: $tar_url"
  curl -fsSL "$tar_url" -o "$tmp_tar"

  rm -rf "$INSTALL_DIR"
  mkdir -p "$INSTALL_DIR"
  tar -xzf "$tmp_tar" --strip-components=1 -C "$INSTALL_DIR"
  rm -f "$tmp_tar"
}

prepare_env() {
  local env_file="$INSTALL_DIR/.env"
  local env_example="$INSTALL_DIR/.env.example"

  [[ -f "$env_example" ]] || {
    err "Missing .env.example in $INSTALL_DIR"
    exit 1
  }

  if [[ ! -f "$env_file" ]]; then
    log "Creating .env from .env.example"
    cp "$env_example" "$env_file"
  fi

  mkdir -p "$MEDIA_ROOT_HOST"/{projects,staging,archive,_review}

  if grep -q '^MEDIA_ROOT_HOST=' "$env_file"; then
    sed -i "s|^MEDIA_ROOT_HOST=.*|MEDIA_ROOT_HOST=$MEDIA_ROOT_HOST|" "$env_file"
  else
    printf '\nMEDIA_ROOT_HOST=%s\n' "$MEDIA_ROOT_HOST" >> "$env_file"
  fi

  if grep -q '^POSTGRES_PASSWORD=' "$env_file" && [[ -n "${POSTGRES_PASSWORD:-}" ]]; then
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" "$env_file"
  fi

  if grep -q '^POSTGRES_PASSWORD=indygestion_strong_password$' "$env_file"; then
    local db_pw
    db_pw="$(gen_secret)"
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$db_pw|" "$env_file"
    log "Generated POSTGRES_PASSWORD"
  fi

  if grep -q '^TUSD_WEBHOOK_SECRET=' "$env_file" && [[ -n "${TUSD_WEBHOOK_SECRET:-}" ]]; then
    sed -i "s|^TUSD_WEBHOOK_SECRET=.*|TUSD_WEBHOOK_SECRET=$TUSD_WEBHOOK_SECRET|" "$env_file"
  fi

  if grep -q '^TUSD_WEBHOOK_SECRET=change-this-to-a-long-random-secret$' "$env_file"; then
    local hook_secret
    hook_secret="$(gen_secret)"
    sed -i "s|^TUSD_WEBHOOK_SECRET=.*|TUSD_WEBHOOK_SECRET=$hook_secret|" "$env_file"
    log "Generated TUSD_WEBHOOK_SECRET"
  fi
}

start_stack() {
  cd "$INSTALL_DIR"

  log "Validating compose config"
  "${COMPOSE_CMD[@]}" config >/dev/null

  if [[ "$AUTO_START" != "true" ]]; then
    warn "AUTO_START=false, skipping startup."
    return
  fi

  log "Building and starting Indygestion"
  "${COMPOSE_CMD[@]}" up -d --build

  log "Current service status"
  "${COMPOSE_CMD[@]}" ps
}

health_checks() {
  [[ "$AUTO_START" == "true" ]] || return 0

  log "Running quick health checks"
  local ok=0
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    log "backend health: OK"
    ok=$((ok + 1))
  else
    warn "backend health check failed"
  fi

  if curl -fsS http://localhost:9000/health >/dev/null 2>&1; then
    log "whisper health: OK"
    ok=$((ok + 1))
  else
    warn "whisper health check failed"
  fi

  if curl -fsSI http://localhost:1080/files/ >/dev/null 2>&1; then
    log "tusd endpoint: OK"
    ok=$((ok + 1))
  else
    warn "tusd endpoint check failed"
  fi

  if [[ "$ok" -lt 2 ]]; then
    warn "Some checks failed. Inspect logs with:"
    warn "cd $INSTALL_DIR && ${COMPOSE_CMD[*]} logs --tail=120"
  fi
}

main() {
  log "Starting Indygestion bootstrap"
  ensure_dependencies
  download_repo
  prepare_env
  start_stack
  health_checks

  log "Done."
  echo
  echo "Install dir : $INSTALL_DIR"
  echo "Media root  : $MEDIA_ROOT_HOST"
  echo "Frontend    : http://localhost:3000"
  echo "Backend API : http://localhost:8000/api/v1"
  echo "Upload tusd : http://localhost:1080/files"
}

main "$@"
