#!/bin/bash

set -euo pipefail

echo "🧩 Setting up Justicier..."

SECRETS_DIR=secrets
WORK_DIR=service

JENKINS_HOME_DIR=$WORK_DIR/jenkins_home
AGENT_SSH_DIR=$WORK_DIR/jenkins_agent_keys
ONEDRIVE_CONF_DIR=$WORK_DIR/onedrive_conf
ONEDRIVE_DATA_DIR=$WORK_DIR/onedrive_data

JENKINS_HOME_DIR_COMPRESSED=$SECRETS_DIR/jenkins_home.zip

AGENT_SSH_PRIV_KEY="$AGENT_SSH_DIR/id_rsa"
AGENT_PUB_KEY="$AGENT_SSH_DIR/id_rsa.pub"

JENKINS_SSH_PRIV_KEY="$AGENT_SSH_DIR/id_rsa"
JENKINS_PUB_KEY="$AGENT_SSH_DIR/id_rsa.pub"

docker compose down

rm -rf $AGENT_SSH_DIR $ONEDRIVE_CONF_DIR $JENKINS_HOME_DIR

mkdir -p "$ONEDRIVE_CONF_DIR" "$ONEDRIVE_DATA_DIR" "$AGENT_SSH_DIR"

# Jenkins config
if [ ! -f $JENKINS_HOME_DIR/config.xml ]; then
  rm -rf "/tmp/justicier"
  mkdir -p "/tmp/justicier"
  unzip -o "$JENKINS_HOME_DIR_COMPRESSED" -d "/tmp/justicier"
  mv "/tmp/justicier/jenkins_home" "$JENKINS_HOME_DIR"
fi

# Generate agent keys if needed
if [ ! -f "$AGENT_SSH_PRIV_KEY" ]; then
    echo "🔐 Generando claves SSH para el agente Jenkins..."
    ssh-keygen -t ed25519 -C "jenkins@agent" -N "" -f $AGENT_SSH_DIR/id_rsa
fi

# Generate Jenkins key
if [ ! -f $JENKINS_HOME_DIR/.ssh/known_hosts ]; then
  cp $AGENT_PUB_KEY $JENKINS_HOME_DIR/.ssh/known_hosts
fi

# Ensure .env file with pubkey
if [ ! -f .env ]; then
  echo "JENKINS_AGENT_SSH_PUBKEY=$(cat $AGENT_SSH_PUB_KEY)" > .env
fi

# OneDrive config
if [ ! -f $ONEDRIVE_CONF_DIR/config ]; then
cat <<EOF > $ONEDRIVE_CONF_DIR/config
sync_dir = "/onedrive/data"
drive_id = "$(cat $SECRETS_DIR/SHAREPOINT_DRIVE_ID)"
skip_dir = "SCANNER"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/_app"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/_output"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/Demos"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/Docs"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/examples"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/parametres"

resync = "true"
resync_auth = "true"
EOF
fi

# OneDrive token
if [ ! -f "$ONEDRIVE_CONF_DIR/refresh_token" ]; then
  cp "$SECRETS_DIR/ONEDRIVE_TOKEN" "$ONEDRIVE_CONF_DIR/refresh_token"
fi


BUILDKIT_PROGRESS=plain docker compose up --build --remove-orphans

