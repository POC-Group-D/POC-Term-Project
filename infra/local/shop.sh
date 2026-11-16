#!/usr/bin/env bash
# Run the Online Boutique on this computer with one command.
#
#   ./shop.sh v1       Demo 1: shop with random recommendations (v1)
#   ./shop.sh v2       Demo 2: shop with AI recommendations (v2) and the local AI model
#   ./shop.sh groq     Browser demo: v2 with Groq Free
#   ./shop.sh watch    show the AI's decisions live (Ctrl+C to stop)
#   ./shop.sh test     check that the shop works
#   ./shop.sh status   show which version is running and where
#   ./shop.sh stop     stop everything and free the memory
set -euo pipefail

cd "$(dirname "$0")"

WITH_V2=(-f docker-compose.yml -f docker-compose.v2.yml)
WITH_GROQ=(-f docker-compose.yml -f docker-compose.groq.yml)

port() {
  local published p
  published="$(docker compose -f docker-compose.yml port frontend 8080 2>/dev/null || true)"
  if [[ -n "$published" ]]; then
    echo "${published##*:}"
    return
  fi
  p="$(grep -E '^FRONTEND_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d '\r ' || true)"
  echo "${FRONTEND_PORT:-${p:-8080}}"
}

# Which recommendation service is running: v1 (random) or v2 (AI)?
running_version() {
  local id endpoint
  id="$(docker ps -q --filter name=online-boutique-recommendationservice 2>/dev/null)"
  if [[ -z "$id" ]]; then
    echo "not running"
    return
  fi
  endpoint="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$id" | sed -n 's/^MODEL_BASE_URL=//p')"
  case "$endpoint" in
    https://api.groq.com/openai/v1) echo "v2 (Groq)" ;;
    http://ollama:11434/v1) echo "v2 (Ollama)" ;;
    '') echo "v1 (random recommendations)" ;;
    *) echo "v2 (AI recommendations)" ;;
  esac
}

# Stop early if another program already uses the shop's port, so nobody opens
# a different shop by mistake.
check_port_free() {
  local p other
  p="$(port)"
  other="$(docker ps --format '{{.Names}} {{.Ports}}' | grep -E ":${p}->" | grep -v '^online-boutique-' | cut -d' ' -f1 || true)"
  if [[ -n "$other" ]]; then
    echo "Port $p is already used by another container: $other" >&2
    echo "That is a different program, not this project's shop. Either stop it, or use another port:" >&2
    echo "  echo FRONTEND_PORT=8081 >> .env" >&2
    exit 1
  fi
}

ready() {
  local url="http://localhost:$(port)" attempt
  echo "Waiting for the shop homepage..."
  for ((attempt = 1; attempt <= 30; attempt++)); do
    if curl --noproxy '*' --fail --silent --max-time 2 --output /dev/null "$url/"; then
      echo "Ready: $url   Recommendations: $(running_version)"
      return
    fi
    sleep 2
  done
  echo "The shop homepage did not become ready at $url." >&2
  docker compose -f docker-compose.yml ps
  return 1
}

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop, wait until it says 'Engine running', then try again." >&2
  exit 1
fi

case "${1:-}" in
  v1)
    check_port_free
    echo "Starting the shop with random recommendations (v1)..."
    # --remove-orphans also stops the AI model containers (the model stays on disk).
    docker compose up -d --build --remove-orphans
    ready
    ;;
  v2)
    check_port_free
    echo "Starting the shop with AI recommendations (v2)..."
    echo "The first run downloads the shop images and the AI model (about 5 GB): 5-15 minutes."
    docker compose "${WITH_V2[@]}" up -d --build
    ready
    echo "The first time you open a product, the AI needs 20-40 s to choose."
    ;;
  groq)
    check_port_free
    echo "Starting the shop with Groq recommendations (v2)..."
    docker compose "${WITH_GROQ[@]}" up -d --build --remove-orphans
    ready
    ;;
  watch)
    exec ./watch-agent.sh
    ;;
  test)
    exec ./smoke-test.sh
    ;;
  status)
    echo "Shop: http://localhost:$(port)   Recommendations: $(running_version)"
    docker compose "${WITH_V2[@]}" ps --format "table {{.Service}}\t{{.Status}}"
    ;;
  stop)
    docker compose "${WITH_V2[@]}" --profile load down --remove-orphans
    echo "Stopped. Downloaded images and the AI model stay on disk, so the next start is quick."
    ;;
  *)
    sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
