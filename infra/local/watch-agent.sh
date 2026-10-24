#!/usr/bin/env bash
# Follow recommendationservice v2 and print one readable line per decision:
#   AGENT     19.5 s | tools: ['recommend'] | tokens: 796 | <model's reason>
# Works from any directory and needs only Docker (the formatter runs with the
# Python inside the v2 image). Stop with Ctrl+C.
set -euo pipefail

# Stop Git Bash on Windows from rewriting container arguments.
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")"

formatter='
import json, sys

for line in sys.stdin:
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if r.get("message") != "recommendation served":
        continue
    outcome = r["outcome"].upper()
    seconds = r["latencyMs"] / 1000
    tools = [c["name"] for c in r["toolCalls"]]
    tokens = r["promptTokens"] + r["completionTokens"]
    detail = r["reason"] or r["fallbackReason"]
    print(f"{outcome:8} {seconds:5.1f} s | tools: {tools} | tokens: {tokens} | {detail}", flush=True)
'

echo "Watching v2 decisions (open product pages in the shop; Ctrl+C to stop)..."
docker compose -f docker-compose.yml -f docker-compose.v2.yml \
  logs --follow --no-log-prefix --tail 0 recommendationservice \
  | docker run --rm -i --entrypoint python poc-group-d/recommendationservice:v2-local -u -c "$formatter"
