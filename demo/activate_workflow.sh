PAT=$(cat secrets/GH_TOKEN)

curl -X POST \
  -H "Authorization: Bearer $PAT" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/ICIQ-DMP/Justicier/actions/workflows/automation.yml/dispatches \
  -d "{
    \"ref\": \"master\",
    \"inputs\": {
      \"naf\": \"$1\",
      \"begin\": \"2023_04\",
      \"end\": \"2023_06\",
      \"author\": \"pepito\"
    }
  }"