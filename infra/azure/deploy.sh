#!/usr/bin/env bash
# Step 2 of the Azure setup: deploy Online Boutique v1, its Container Apps
# environment, Log Analytics and the free-tier Cosmos DB account.
#
# Refuses to run until guardrails.sh has created the budget.
#
# The frontend and product catalog use our 200-product images from GHCR
# (IMAGE_TAG, default "latest"); recommendationservice is upstream v1.
#
# Usage:
#   ./deploy.sh              # deploy / update everything
#   ./deploy.sh --what-if    # preview the changes without applying them
#   IMAGE_TAG=sha-1a2b3c4 ./deploy.sh   # deploy a specific build
set -euo pipefail
source "$(dirname "$0")/common.sh"

require_login

budget_state="$(az deployment group show --resource-group "$AZ_RESOURCE_GROUP" --name budget \
  --query properties.provisioningState --output tsv 2>/dev/null || true)"
if [[ "$budget_state" != "Succeeded" ]]; then
  echo "No budget found on $AZ_RESOURCE_GROUP. Run ./guardrails.sh first." >&2
  exit 1
fi

# Only one free-tier Cosmos DB account is allowed per subscription. If it is
# already used elsewhere, skip Cosmos DB rather than create a billed account.
existing_free_tier="$(az cosmosdb list \
  --query "[?enableFreeTier && resourceGroup!='$AZ_RESOURCE_GROUP'] | length(@)" --output tsv)"
deploy_cosmos=true
if [[ "$existing_free_tier" != "0" ]]; then
  echo "This subscription already uses its Cosmos DB free tier elsewhere; skipping Cosmos DB." >&2
  deploy_cosmos=false
fi

action=create
if [[ "${1:-}" == "--what-if" ]]; then
  action=what-if
fi

az deployment group "$action" \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --name online-boutique \
  --template-file main.bicep \
  --parameters \
      location="$AZ_LOCATION" \
      namePrefix="$AZ_NAME_PREFIX" \
      deployCosmos="$deploy_cosmos" \
      cosmosLocation="$AZ_COSMOS_LOCATION" \
      frontendImage="$GHCR_PREFIX/frontend:$IMAGE_TAG" \
      productCatalogImage="$GHCR_PREFIX/productcatalogservice-200:$IMAGE_TAG"

if [[ "$action" == "create" ]]; then
  url="$(az deployment group show --resource-group "$AZ_RESOURCE_GROUP" --name online-boutique \
    --query properties.outputs.frontendUrl.value --output tsv)"
  echo
  echo "Shop URL: $url"
  echo "Apps scale to zero when idle; the first request after a pause takes ~30-60 s."
  echo "Check it with: ./smoke-test.sh"
fi
