#!/usr/bin/env bash
# Follow recommendationservice v2 and print one readable line per decision:
#   AGENT 19.5 s | tools: ['recommend'] | tokens: 796 | <model's reason>
# Works from any directory. Stop with Ctrl+C.
set -euo pipefail

cd "$(dirname "$0")"

docker compose -f docker-compose.yml -f docker-compose.v2.yml \
  logs --follow --no-log-prefix --tail 0 recommendationservice \
  | python -u -c '
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
    print(f"{outcome:8} {seconds:5.1f} s | tools: {tools} | tokens: {tokens} | {detail}")
'
