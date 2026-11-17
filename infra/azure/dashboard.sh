#!/usr/bin/env bash
# Create or update the canary dashboard (an Azure Monitor workbook comparing
# v1 and v2, defined in dashboard.bicep) and print its link. Free of charge.
#
#   ./dashboard.sh
set -euo pipefail
source "$(dirname "$0")/common.sh"

require_login
id="$(az deployment group create --resource-group "$AZ_RESOURCE_GROUP" --name canary-dashboard \
  --template-file dashboard.bicep --query properties.outputs.dashboardId.value --output tsv)"
echo
echo "Canary dashboard: https://portal.azure.com/#resource$id/workbook"
echo "(Azure portal > Monitor > Workbooks > Canary dashboard: recommendationservice v1 vs v2)"
