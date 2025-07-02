#!/bin/bash
# Exit script on error
set -e
echo "Preparing environment for Jenkins deployment..."
# Define SSH keys directory
JENKINS_AGENT_KEYS_DIR="jenkins_agent_keys"
# Create SSH keys directory
echo "Creating SSH keys directory for Jenkins Agent..."
mkdir -p "${JENKINS_AGENT_KEYS_DIR}"
# Generate SSH keys for Jenkins Agent
echo "Generating SSH keys for Jenkins Agent..."
file_name=id_rsa
if [ ! -f "$JENKINS_AGENT_KEYS_DIR/${file_name}" ]; then
  ssh-keygen -t ed25519 -f "$JENKINS_AGENT_KEYS_DIR/${file_name}" -N "" -C "jenkins@agent" -f "$JENKINS_AGENT_KEYS_DIR/${file_name}"
  chmod 600 "$JENKINS_AGENT_KEYS_DIR/${file_name}"
  chmod 644 "$JENKINS_AGENT_KEYS_DIR/${file_name}.pub"
else
  echo "SSH keys already exist. Skipping key generation."
fi
# Copy public key to authorized_keys
echo "Configuring authorized_keys for Jenkins Agent..."
cp "$JENKINS_AGENT_KEYS_DIR/${file_name}.pub" "$JENKINS_AGENT_KEYS_DIR/authorized_keys"
chmod 644 "$JENKINS_AGENT_KEYS_DIR/authorized_keys"

# Ensure everything is ready
echo "Environment setup is complete!"
echo "You can now run 'docker-compose up -d' to start Jenkins."
BUILDKIT_PROGRESS=plain docker compose up --build