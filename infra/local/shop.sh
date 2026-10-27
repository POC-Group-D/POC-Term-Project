#!/usr/bin/env bash
# Run the Online Boutique on this computer with one command.
#
#   ./shop.sh v2       start the shop with the AI agent (v2) and the local AI model
#   ./shop.sh v1       start the shop with the original random recommendations (v1)
#   ./shop.sh watch    show the AI agent's decisions live (Ctrl+C to stop)
#   ./shop.sh test     check that the shop works
#   ./shop.sh status   list the running containers
#   ./shop.sh stop     stop everything and free the memory
set -euo pipefail

cd "$(dirname "$0")"

WITH_V2=(-f docker-compose.yml -f docker-compose.v2.yml)

port() {
  local p
  p="$(grep -E '^FRONTEND_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d '\r ' || true)"
  echo "${p:-8080}"
}

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop, wait until it says 'Engine running', then try again." >&2
  exit 1
fi

case "${1:-}" in
  v2)
    echo "Starting the shop with the AI agent (v2)."
    echo "The first run downloads the shop images and the AI model (about 5 GB), so it can take 5-15 minutes."
    docker compose "${WITH_V2[@]}" up -d --build
    echo
    echo "Ready: http://localhost:$(port)"
    echo "Open any product. The first time, the AI takes about 20-40 s to pick the 'You May Also Like' products."
    echo "See the AI's decisions with: ./shop.sh watch"
    ;;
  v1)
    echo "Starting the shop with the original random recommendations (v1)."
    # --remove-orphans also stops the AI model containers (the model stays on disk).
    docker compose up -d --build --remove-orphans
    echo
    echo "Ready: http://localhost:$(port)"
    ;;
  watch)
    exec ./watch-agent.sh
    ;;
  test)
    exec ./smoke-test.sh
    ;;
  status)
    docker compose "${WITH_V2[@]}" ps --format "table {{.Service}}\t{{.Status}}"
    ;;
  stop)
    docker compose "${WITH_V2[@]}" --profile load down --remove-orphans
    echo "Stopped. Downloaded images and the AI model stay on disk, so the next start is quick."
    ;;
  *)
    sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
