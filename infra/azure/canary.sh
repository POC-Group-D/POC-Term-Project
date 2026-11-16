#!/usr/bin/env bash
# Run v1 and v2 of recommendationservice side by side on Azure and choose
# how much of the shop's traffic goes to v2 (the AI agent on Groq).
#
#   ./canary.sh deploy     add a new v2 revision next to v1, with 0% traffic
#   ./canary.sh 10         send 10% of recommendation requests to v2 (any 0-100)
#   ./canary.sh rollback   send all traffic back to v1
#   ./canary.sh status     show both versions and their traffic share
#   ./canary.sh watch      show v2's decisions live (Ctrl+C to stop)
#
# The facade is Container Apps traffic splitting between the two revisions,
# which carry the labels "v1" and "v2". The frontend keeps calling
# recommendationservice:80 and cannot tell which version answered.
set -euo pipefail
source "$(dirname "$0")/common.sh"

APP=recommendationservice
ARGS=(--resource-group "$AZ_RESOURCE_GROUP" --name "$APP")
V2_IMAGE="$GHCR_PREFIX/recommendationservice-v2:$IMAGE_TAG"

# Name of the revision that carries a label ("v1" or "v2"), or nothing.
label_of() {
  az containerapp show "${ARGS[@]}" \
    --query "properties.configuration.ingress.traffic[?label=='$1'].revisionName | [0]" --output tsv
}

# Read GROQ_API_KEY from the environment, infra/local/.env, or a hidden prompt.
groq_key() {
  local key="${GROQ_API_KEY:-}"
  if [[ -z "$key" && -f ../local/.env ]]; then
    key="$(grep -E '^GROQ_API_KEY=' ../local/.env | head -1 | cut -d= -f2- | tr -d '\r "'"'" || true)"
  fi
  if [[ -z "$key" ]]; then
    read -rs -p "Groq API key (input hidden): " key
    echo >&2
  fi
  [[ -n "$key" ]] || { echo "A Groq API key is required." >&2; exit 1; }
  echo "$key"
}

set_v2_share() {
  local v2_share="$1"
  [[ -n "$(label_of v2)" ]] || { echo "No v2 revision yet. Run: ./canary.sh deploy" >&2; exit 1; }
  az containerapp ingress traffic set "${ARGS[@]}" \
    --label-weight "v1=$((100 - v2_share))" "v2=$v2_share" --output none
  echo "Traffic: v1 $((100 - v2_share))%, v2 ${v2_share}%"
}

deploy() {
  # Container Apps must keep several revisions active to split traffic.
  az containerapp revision set-mode "${ARGS[@]}" --mode multiple --output none

  # v1 is the revision running the unmodified upstream image.
  local v1
  v1="$(label_of v1)"
  if [[ -z "$v1" ]]; then
    v1="$(az containerapp revision list "${ARGS[@]}" \
      --query "[?contains(properties.template.containers[0].image, '/recommendationservice:')] | sort_by(@, &properties.createdTime) | [-1].name" \
      --output tsv)"
    [[ -n "$v1" ]] || { echo "Could not find the v1 revision." >&2; exit 1; }
  fi

  # Secrets live in Azure, never in the repository.
  local cosmos_account cosmos_endpoint
  cosmos_account="$(az deployment group show --resource-group "$AZ_RESOURCE_GROUP" --name online-boutique \
    --query properties.outputs.cosmosAccountName.value --output tsv)"
  cosmos_endpoint="$(az cosmosdb show --resource-group "$AZ_RESOURCE_GROUP" --name "$cosmos_account" \
    --query documentEndpoint --output tsv)"
  az containerapp secret set "${ARGS[@]}" --output none --secrets \
    "groq-key=$(groq_key)" \
    "cosmos-key=$(az cosmosdb keys list --resource-group "$AZ_RESOURCE_GROUP" --name "$cosmos_account" \
      --query primaryMasterKey --output tsv)"

  # v2 = v1's settings (port, catalog address) + the agent image and model.
  local suffix v2
  suffix="v2-$(date +%m%d-%H%M)"
  v2="$APP--$suffix"
  echo "Creating $v2 from $V2_IMAGE"
  az containerapp revision copy "${ARGS[@]}" --from-revision "$v1" --revision-suffix "$suffix" \
    --image "$V2_IMAGE" --output none --set-env-vars \
    MODEL_BASE_URL=https://api.groq.com/openai/v1 MODEL_API_KEY=secretref:groq-key \
    MODEL_NAME=openai/gpt-oss-20b MODEL_MAX_TOKENS=600 MODEL_REASONING_EFFORT=low \
    MODEL_TOOL_CHOICE=recommend MAX_AGENT_STEPS=1 SHORTLIST_SIZE=12 \
    "COSMOS_ENDPOINT=$cosmos_endpoint" COSMOS_KEY=secretref:cosmos-key

  az containerapp revision label add "${ARGS[@]}" --revision "$v1" --label v1 --yes --output none
  az containerapp revision label add "${ARGS[@]}" --revision "$v2" --label v2 --yes --output none
  set_v2_share 0
  echo "Next: ./canary.sh 100 (all traffic to v2) or ./canary.sh 10 (a canary step)."
}

show_status() {
  az containerapp show "${ARGS[@]}" \
    --query "properties.configuration.ingress.traffic[].{label:label, revision:revisionName, percent:weight}" \
    --output table
}

watch_v2() {
  local v2
  v2="$(label_of v2)"
  [[ -n "$v2" ]] || { echo "No v2 revision yet. Run: ./canary.sh deploy" >&2; exit 1; }
  echo "Watching v2 decisions on Azure (open product pages in the shop; Ctrl+C to stop)..."
  az containerapp logs show "${ARGS[@]}" --revision "$v2" --type console --follow --tail 0 --format text \
    | python -u -c '
import json, sys
for line in sys.stdin:
    start = line.find("{")
    try:
        r = json.loads(line[start:])
    except ValueError:
        continue
    if start < 0 or r.get("message") != "recommendation served":
        continue
    outcome = r["outcome"].upper()
    seconds = r["latencyMs"] / 1000
    tokens = r["promptTokens"] + r["completionTokens"]
    detail = r["reason"] or r["fallbackReason"]
    model = r["model"]
    print(f"{outcome:8} {seconds:5.1f} s | model: {model} | tokens: {tokens} | {detail}", flush=True)
'
}

case "${1:-}" in
  deploy)   require_login; deploy ;;
  rollback) require_login; set_v2_share 0 ;;
  status)   require_login; show_status ;;
  watch)    require_login; watch_v2 ;;
  [0-9]|[0-9][0-9]|100) require_login; set_v2_share "$1" ;;
  *)
    sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
