#!/usr/bin/env bash

set -euo pipefail

# === CONFIG ===
COMPOSE_FILE="compose.yml"
DIRS=("jenkins_home" "onedrive_conf" "onedrive_data")
PODMAN_COMPOSE_BIN="/usr/local/bin/podman-compose"

# === COLORS ===
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RESET='\033[0m'

# === FUNCTIONS ===

log() {
  echo -e "${GREEN}✔ $1${RESET}"
}

warn() {
  echo -e "${YELLOW}➜ $1${RESET}"
}

# === STEP 1: Install Podman if missing ===
if ! command -v podman &> /dev/null; then
  warn "Podman not found. Installing..."
  sudo apt update && sudo apt install -y podman
else
  log "Podman is already installed."
fi

# === STEP 2: Install podman-compose if missing ===
if ! command -v podman-compose &> /dev/null; then
  warn "podman-compose not found. Installing via pip..."
  python3 -m pip install --user --upgrade pip
  python3 -m pip install --user podman-compose
  export PATH="$HOME/.local/bin:$PATH"
  if ! grep -q ".local/bin" <<< "$PATH"; then
    warn "You may want to add '$HOME/.local/bin' to your PATH."
  fi
else
  log "podman-compose is already installed."
fi

docker compose down

# === STEP 3: Ensure required directories exist ===
for dir in "${DIRS[@]}"; do
  if [ ! -d "$dir" ]; then
    mkdir -p "$dir"
    log "Created directory ./$dir"
  else
    log "Directory ./$dir already exists"
  fi
done

# === STEP 4: Ensure content in volume directories ===
drive_id=$(cat secrets/DRIVE_ID)
cat <<EOF > onedrive_conf/config
sync_dir = "/onedrive/data"
drive_id = "$drive_id"
EOF

onedrive_token=$(cat secrets/ONEDRIVE_TOKEN)
cat <<EOF > onedrive_conf/refresh_token
$onedrive_token
EOF

export JENKINS_AGENT_SSH_PUBKEY="$(cat secrets/jenkins_key.pub)"
#podman rm -f workflow_jenkins_1
#podman rm -f workflow_agent_1

# === STEP 5: Start containers with podman-compose ===
if [ -f "$COMPOSE_FILE" ]; then
  log "Running podman-compose up..."
  docker compose up
  log "Services are up and running."
else
  echo "❌ $COMPOSE_FILE not found. Please ensure it's in the current directory."
  exit 1
fi