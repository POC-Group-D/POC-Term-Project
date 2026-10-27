#!/usr/bin/env bash
# Turn the Azure shop on and off.
#
#   ./cloud.sh status   is it on or off, and how many copies are running
#   ./cloud.sh start    turn the shop on (before Demo 3); ready in about 3-5 minutes
#   ./cloud.sh stop     turn the shop off (after the demo): no compute costs at all
#
# Why "stop": the public address gets visits from internet bots even when
# nobody uses the shop, which keeps apps awake and slowly uses the student
# credit. A stopped app runs nothing and costs nothing; its settings are kept.
# Cosmos DB (free tier) and Log Analytics (capped) stay as they are.
set -euo pipefail
source "$(dirname "$0")/common.sh"

API_VERSION=2026-07-01

app_url() {
  local sub
  sub="$(az account show --query id --output tsv)"
  echo "https://management.azure.com/subscriptions/$sub/resourceGroups/$AZ_RESOURCE_GROUP/providers/Microsoft.App/containerApps/$1"
}

show_status() {
  printf "%-24s %-10s %s\n" "APP" "STATE" "RUNNING COPIES"
  for app in "${APPS[@]}"; do
    state="$(az rest --method get --url "$(app_url "$app")?api-version=$API_VERSION" \
      --query properties.runningStatus --output tsv 2>/dev/null || echo "missing")"
    copies="$(az containerapp replica list --resource-group "$AZ_RESOURCE_GROUP" --name "$app" \
      --query 'length(@)' --output tsv 2>/dev/null || echo 0)"
    printf "%-24s %-10s %s\n" "$app" "$state" "$copies"
  done
}

case "${1:-}" in
  status)
    require_login
    show_status
    ;;
  start)
    require_login
    for app in "${APPS[@]}"; do
      echo "Starting $app"
      az rest --method post --url "$(app_url "$app")/start?api-version=$API_VERSION" --output none
    done
    url="$(az deployment group show --resource-group "$AZ_RESOURCE_GROUP" --name online-boutique \
      --query properties.outputs.frontendUrl.value --output tsv)"
    echo
    echo "The shop is on. Wake it up and check it (takes about 3 minutes):"
    echo "  ./smoke-test.sh $url"
    echo "Turn it off after the demo with: ./cloud.sh stop"
    ;;
  stop)
    require_login
    for app in "${APPS[@]}"; do
      echo "Stopping $app"
      az rest --method post --url "$(app_url "$app")/stop?api-version=$API_VERSION" --output none
    done
    echo
    echo "The shop is off: nothing is running, so it uses no credit."
    echo "Turn it on before the next demo with: ./cloud.sh start"
    ;;
  *)
    sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
