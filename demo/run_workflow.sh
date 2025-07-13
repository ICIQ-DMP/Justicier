export PROJECT_FOLDER="$(cd "$(dirname "$(realpath "$0")")/.." &>/dev/null && pwd)"

# Set your variables
#JENKINS_URL="http://localhost:8080"
JENKINS_URL="https://workflows.iciq.es:8080"
USER="Justicier"
API_TOKEN="$(cat $PROJECT_FOLDER/secrets/JENKINS_API_TOKEN)"
JOB="run-justicier"
BUILD_TOKEN="$(cat $PROJECT_FOLDER/secrets/JENKINS_BUILD_TOKEN)"
ID_VALUE="2"

# Step 1: Get crumb
request=$(curl -s -u "$USER:$API_TOKEN" "$JENKINS_URL/crumbIssuer/api/json")
CRUMB=$(echo "$request" | jq -r '.crumb')

# Step 2: Trigger build with crumb and parameters
curl -X POST "$JENKINS_URL/job/$JOB/buildWithParameters?token=$BUILD_TOKEN&ID=$ID_VALUE&cause=automated+workflow" \
     -u "$USER:$API_TOKEN" \
     -H "Jenkins-Crumb:$CRUMB"