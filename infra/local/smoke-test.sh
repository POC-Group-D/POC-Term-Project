#!/usr/bin/env bash
# Run smoke_test.py against the running local stack (v1 or v2).
# Usage: ./smoke-test.sh   (from infra/local, after `docker compose up -d`)
#
# The test runs in the v1 recommendationservice image only because that image
# already contains grpcio and the generated stubs; it calls whichever version
# is currently serving.
set -euo pipefail

# Stop Git Bash on Windows from rewriting the container paths below.
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")"

docker compose -f docker-compose.yml build --quiet recommendationservice

docker run --rm \
  --network online-boutique_default \
  --volume "$(pwd)/smoke_test.py:/smoke/smoke_test.py:ro" \
  --env PYTHONPATH=/recommendationservice \
  --entrypoint python \
  poc-group-d/recommendationservice:local /smoke/smoke_test.py
