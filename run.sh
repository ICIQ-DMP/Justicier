#!/bin/bash

ensure_dotenv()
{
  cat <<EOF > .env
JENKINS_AGENT_SSH_PUBKEY=$(sudo cat ${AGENT_SSH_PUBLIC_KEY_PATH})
FIREWALL_PORT_EXTERNAL=${FIREWALL_PORT_EXTERNAL}
FIREWALL_PORT_INTERNAL=${FIREWALL_PORT_INTERNAL}
JENKINS_PORT_INTERNAL=${JENKINS_PORT_INTERNAL}
AGENT_PORT_INTERNAL=${AGENT_PORT_INTERNAL}
EOF
}

export ROOT="$(cd "$(dirname "$(realpath "$0")")" &>/dev/null && pwd)"

set -euo pipefail

echo "🧩 Setting up Justicier..."

SECRETS_DIR="${ROOT}/secrets"
WORK_DIR="${ROOT}/service"

JENKINS_HOME_DIR="${WORK_DIR}/jenkins_home"
ONEDRIVE_CONF_DIR="${WORK_DIR}/onedrive_conf"
ONEDRIVE_DATA_DIR="${WORK_DIR}/onedrive_data"
ONEDRIVE_LOG_DIR="${WORK_DIR}/onedrive_logs"
NGINX_LOG_DIR="${WORK_DIR}/nginx_logs"
NGINX_CONF_DIR="${WORK_DIR}/nginx_conf"
AGENT_SSH_DIR="${WORK_DIR}/jenkins_agent_keys"
AGENT_SSH_PRIVATE_KEY_PATH="${AGENT_SSH_DIR}/id_rsa"
AGENT_SSH_PUBLIC_KEY_PATH="${AGENT_SSH_DIR}/id_rsa.pub"
HOSTNAME="$(cat "${SECRETS_DIR}/HOSTNAME")"
#HOSTNAME="localhost"  # For dev mode
ADMIN_IP="$(cat "${SECRETS_DIR}/ADMIN_IP")"
JENKINS_PORT_INTERNAL="$(cat "${SECRETS_DIR}/JENKINS_PORT_INTERNAL")"
FIREWALL_PORT_EXTERNAL="$(cat "${SECRETS_DIR}/FIREWALL_PORT_EXTERNAL")"
FIREWALL_PORT_INTERNAL="$(cat "${SECRETS_DIR}/FIREWALL_PORT_INTERNAL")"
AGENT_PORT_INTERNAL="$(cat "${SECRETS_DIR}/AGENT_PORT_INTERNAL")"
AGENT_SSH_PUBLIC_KEY="$(cat "${SECRETS_DIR}/AGENT_SSH_PUBLIC_KEY")"
AGENT_SSH_PRIVATE_KEY="$(cat "${SECRETS_DIR}/AGENT_SSH_PRIVATE_KEY")"
JENKINS_HOME_DIR_COMPRESSED="${SECRETS_DIR}/jenkins_home.zip"
decompress_temp_dir=/tmp/justicier

# Stop containers only if .env present
if [ -f .env ]; then
  docker compose down
fi

rm -rf "${ONEDRIVE_CONF_DIR}/items.sqlite3" "${ONEDRIVE_CONF_DIR}/items.sqlite3-shm" "${ONEDRIVE_CONF_DIR}/items.sqlite3-wal" "${ONEDRIVE_CONF_DIR}/.config.hash" "${ONEDRIVE_CONF_DIR}/.config.backup" "${NGINX_CONF_DIR}"

mkdir -p "${JENKINS_HOME_DIR}" "${ONEDRIVE_CONF_DIR}" "${ONEDRIVE_DATA_DIR}" "${AGENT_SSH_DIR}" "${NGINX_CONF_DIR}" "${NGINX_LOG_DIR}" "${ONEDRIVE_LOG_DIR}"

# Jenkins config
if [ ! -f "${JENKINS_HOME_DIR}/config.xml" ]; then
  unzip -o "${JENKINS_HOME_DIR_COMPRESSED}" -d "${WORK_DIR}"
fi

if [ ! -f "${AGENT_SSH_PUBLIC_KEY_PATH}" ]; then
  echo "${AGENT_SSH_PUBLIC_KEY}" | sudo tee "${AGENT_SSH_PUBLIC_KEY_PATH}" > /dev/null
fi
if [ ! -f "${AGENT_SSH_PRIVATE_KEY_PATH}" ]; then
  echo "${AGENT_SSH_PRIVATE_KEY}" | sudo tee "${AGENT_SSH_PRIVATE_KEY_PATH}" > /dev/null
fi

ensure_dotenv

echo precat
# OneDrive config
if [ ! -f "${ONEDRIVE_CONF_DIR}/config" ]; then
  cat <<EOF > ${ONEDRIVE_CONF_DIR}/config
sync_dir = "/onedrive/data"
drive_id = "$(cat $SECRETS_DIR/SHAREPOINT_DRIVE_ID)"
skip_dir = "SCANNER"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/_app"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/_templates"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/_output"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/Demos"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/Docs"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/examples"
skip_dir = "$(cat $SECRETS_DIR/SHAREPOINT_FOLDER)/parametres"

log_dir = "/onedrive/logs/"

sync_dir_permissions = "755"
sync_file_permissions = "644"

resync = "true"
resync_auth = "true"
EOF
echo postcat
fi

# OneDrive token
if [ ! -f "${ONEDRIVE_CONF_DIR}/refresh_token" ]; then
  cp "${SECRETS_DIR}/ONEDRIVE_TOKEN" "${ONEDRIVE_CONF_DIR}/refresh_token"
fi

cat <<EOF > ${NGINX_CONF_DIR}/proxy_params
proxy_set_header Host \$host;
proxy_set_header X-Real-IP \$remote_addr;
proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Host workflows.iciq.es;
proxy_set_header X-Forwarded-Proto \$scheme;
EOF

cat <<EOF > ${NGINX_CONF_DIR}/nginx.conf
events {}

http {
    server {
        listen ${FIREWALL_PORT_INTERNAL};
        server_name ${HOSTNAME};

        access_log /var/log/nginx/jenkins.access.log;
        error_log  /var/log/nginx/jenkins.error.log;

        location = /crumbIssuer/api/json {
            if (\$request_method != "GET") {
                return 403;
            }
            proxy_pass http://jenkins:${JENKINS_PORT_INTERNAL};
            include /etc/nginx/proxy_params;
        }

        location = /job/run-justicier/buildWithParameters {
            if (\$request_method != "POST") {
                return 403;
            }
            proxy_pass http://jenkins:${JENKINS_PORT_INTERNAL};
            include /etc/nginx/proxy_params;
        }

        location / {
            allow ${ADMIN_IP};  # IP access
            #allow 172.19.0.1;   # Docker host access (only when using default network)
            allow 127.0.0.1;    # Within the container access
            deny all;

            proxy_pass http://jenkins:${JENKINS_PORT_INTERNAL};
            include /etc/nginx/proxy_params;
        }
        location /healthz {
          return 200 'OK';
          add_header Content-Type text/plain;
        }
    }
}
EOF

BUILDKIT_PROGRESS=plain docker compose up --build --remove-orphans -d

cd "${ROOT}/service"
zip -r "${JENKINS_HOME_DIR_COMPRESSED}" jenkins_home
exit 0
 
