# Shared settings for the Azure scripts. Sourced, not executed.
# Override any value by exporting it before running a script, e.g.
#   AZ_LOCATION=eastus ./deploy.sh

AZ_SUBSCRIPTION="${AZ_SUBSCRIPTION:-Azure for Students}"
AZ_RESOURCE_GROUP="${AZ_RESOURCE_GROUP:-rg-poc-group-d}"
AZ_LOCATION="${AZ_LOCATION:-canadacentral}"
AZ_NAME_PREFIX="${AZ_NAME_PREFIX:-poc-gd}"
AZ_BUDGET_AMOUNT="${AZ_BUDGET_AMOUNT:-10}"

AZ_TAGS=(project=poc-group-d course=coen6313 environment=dev)

# Container Apps that make up the shop, in the order they should start.
APPS=(
  productcatalogservice currencyservice cartservice paymentservice
  shippingservice emailservice adservice recommendationservice
  checkoutservice frontend
)

# Run from this folder and pass template paths relatively: on Windows the
# Azure CLI cannot read Git Bash style absolute paths such as /d/...
cd "$(dirname "${BASH_SOURCE[0]}")"

# Stop Git Bash on Windows from rewriting resource IDs that start with "/".
export MSYS_NO_PATHCONV=1

# Make sure we are logged in and pinned to the project subscription, so a
# script never creates resources in another (e.g. university) subscription.
require_login() {
  if ! az account show --output none 2>/dev/null; then
    echo "Not logged in to Azure. Run: az login" >&2
    exit 1
  fi
  if ! az account set --subscription "$AZ_SUBSCRIPTION" 2>/dev/null; then
    echo "Subscription '$AZ_SUBSCRIPTION' not found for this login." >&2
    exit 1
  fi
  echo "Subscription: $(az account show --query name --output tsv)"
}
