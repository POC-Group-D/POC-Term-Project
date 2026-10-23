#!/usr/bin/env bash
# Check the deployed shop end to end through its public URL:
#   - home page and a product page return 200
#   - the product page renders the "You May Also Like" recommendations,
#     which proves frontend -> recommendationservice -> productcatalog gRPC works
#   - adding to the cart and checking out succeeds (cart, Redis sidecar,
#     checkout, payment, shipping, email, currency)
#
# Usage: ./smoke-test.sh [frontend-url]
set -euo pipefail
source "$(dirname "$0")/common.sh"

url="${1:-}"
if [[ -z "$url" ]]; then
  require_login
  url="$(az deployment group show --resource-group "$AZ_RESOURCE_GROUP" --name online-boutique \
    --query properties.outputs.frontendUrl.value --output tsv)"
fi
url="${url%/}"
product_id="OLJCESPC7Z"
cookies="$(mktemp)"
trap 'rm -f "$cookies"' EXIT

failures=0
check() {
  local name="$1"; shift
  if "$@"; then
    echo "PASS  $name"
  else
    echo "FAIL  $name"
    failures=$((failures + 1))
  fi
}

http_ok() {
  [[ "$(curl -s -o /dev/null -w '%{http_code}' -b "$cookies" -c "$cookies" --max-time 90 "$@")" == "200" ]]
}

has_recommendations() {
  curl -s -b "$cookies" -c "$cookies" --max-time 90 "$url/product/$product_id" \
    | grep -q 'You May Also Like'
}

echo "Testing $url (the first request may take up to a minute while apps scale from zero)"
check "home page" http_ok "$url/"
check "product page" http_ok "$url/product/$product_id"
check "recommendations rendered" has_recommendations
check "add to cart" http_ok -L -X POST -d "product_id=$product_id&quantity=1" "$url/cart"
check "checkout" http_ok -L -X POST \
  -d "email=smoke@example.com&street_address=1455 De Maisonneuve Blvd W&zip_code=94043" \
  -d "city=Montreal&state=QC&country=Canada&credit_card_number=4432801561520454" \
  -d "credit_card_expiration_month=1&credit_card_expiration_year=2030&credit_card_cvv=672" \
  "$url/cart/checkout"

echo
echo "$((5 - failures))/5 checks passed"
exit $((failures > 0))
