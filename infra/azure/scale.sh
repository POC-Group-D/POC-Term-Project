#!/usr/bin/env bash
# Switch every app between scale-to-zero (default, no idle cost) and
# always-on (for a demo or a canary run, avoids cold starts).
#
# Usage:
#   ./scale.sh up     # min replicas = 1 (billed while running)
#   ./scale.sh down   # min replicas = 0 (back to free when idle)
set -euo pipefail
source "$(dirname "$0")/common.sh"

case "${1:-}" in
  up) min=1 ;;
  down) min=0 ;;
  *) echo "Usage: $0 up|down" >&2; exit 1 ;;
esac

require_login

for app in "${APPS[@]}"; do
  echo "Setting $app min replicas to $min"
  az containerapp update \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --name "$app" \
    --min-replicas "$min" \
    --output none
done

if [[ "$min" == 1 ]]; then
  echo "All apps are always on. Run '$0 down' when you finish, to stop idle charges."
fi
