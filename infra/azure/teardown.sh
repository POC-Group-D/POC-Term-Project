#!/usr/bin/env bash
# Delete everything the project created in Azure (the whole resource group,
# including the budget and the Cosmos DB data). This cannot be undone.
#
# Usage: ./teardown.sh
set -euo pipefail
source "$(dirname "$0")/common.sh"

require_login

read -r -p "Delete resource group '$AZ_RESOURCE_GROUP' and everything in it? Type its name to confirm: " answer
if [[ "$answer" != "$AZ_RESOURCE_GROUP" ]]; then
  echo "Aborted."
  exit 1
fi

az group delete --name "$AZ_RESOURCE_GROUP" --yes --no-wait
echo "Deletion started. Check progress with: az group show --name $AZ_RESOURCE_GROUP"
