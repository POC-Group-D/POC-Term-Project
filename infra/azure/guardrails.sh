#!/usr/bin/env bash
# Step 1 of the Azure setup: cost guardrails. Run this before deploy.sh.
#   - registers the resource providers the project uses
#   - creates the tagged resource group
#   - creates a monthly budget with alerts at 50%, 80% and 100%
#
# None of these resources are billable.
#
# Usage: ./guardrails.sh you@example.com [teammate@example.com ...]
set -euo pipefail
source "$(dirname "$0")/common.sh"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <alert-email> [more-emails...]" >&2
  exit 1
fi

require_login

echo "Registering resource providers (first run can take a few minutes)..."
for provider in Microsoft.App Microsoft.OperationalInsights Microsoft.DocumentDB Microsoft.Consumption; do
  az provider register --namespace "$provider" --wait --output none
done

echo "Creating resource group $AZ_RESOURCE_GROUP in $AZ_LOCATION..."
az group create \
  --name "$AZ_RESOURCE_GROUP" \
  --location "$AZ_LOCATION" \
  --tags "${AZ_TAGS[@]}" \
  --output none

emails_json="$(printf '"%s",' "$@")"
emails_json="[${emails_json%,}]"

echo "Creating budget of \$$AZ_BUDGET_AMOUNT/month with alerts at 50/80/100%..."
az deployment group create \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --name budget \
  --template-file budget.bicep \
  --parameters amount="$AZ_BUDGET_AMOUNT" contactEmails="$emails_json" \
  --output none

echo "Guardrails in place. Next: ./deploy.sh"
