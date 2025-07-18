export PROJECT_FOLDER="$(cd "$(dirname "$(realpath "$0")")/.." &>/dev/null && pwd)"

# Set your variables
#JENKINS_URL="http://localhost:$(cat "${PROJECT_FOLDER}/secrets/FIREWALL_PORT_EXTERNAL")"
#JENKINS_URL="https://$(cat "${PROJECT_FOLDER}/secrets/HOSTNAME")"
JENKINS_URL="http://$(cat "${PROJECT_FOLDER}/secrets/HOSTNAME")"

USER="Justicier"
API_TOKEN="$(cat $PROJECT_FOLDER/secrets/JENKINS_API_TOKEN)"
JOB="run-justicier"
BUILD_TOKEN="$(cat $PROJECT_FOLDER/secrets/JENKINS_BUILD_TOKEN)"
ID_VALUE="16"

# Step 1: Get crumb
request=$(curl -s -u "$USER:$API_TOKEN" "$JENKINS_URL/crumbIssuer/api/json")
echo $request
CRUMB=$(echo "$request" | jq -r '.crumb')

# Step 2: Trigger build with crumb and parameters
curl -v -X POST "$JENKINS_URL/job/$JOB/buildWithParameters?token=$BUILD_TOKEN&ID=$ID_VALUE&cause=automated+workflow" \
     -u "$USER:$API_TOKEN" \
     -H "Jenkins-Crumb:$CRUMB"
