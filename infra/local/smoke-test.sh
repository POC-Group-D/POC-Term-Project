#!/usr/bin/env bash
# Run smoke_test.py against the running local stack.
# Usage: ./smoke-test.sh   (from infra/local, after `docker compose up -d`)
set -euo pipefail

# Stop Git Bash on Windows from rewriting the container paths below.
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")"

docker compose run --rm --no-deps \
  --volume "$(pwd)/smoke_test.py:/smoke/smoke_test.py:ro" \
  --env PYTHONPATH=/recommendationservice \
  --entrypoint python \
  recommendationservice /smoke/smoke_test.py
