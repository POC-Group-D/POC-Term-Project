# Phase 3, item 7: recommendationservice v2 AI agent

- Date: 2026-10-23
- Member: Nofil Siddiqui
- Tool and model: Claude Code desktop app, Claude Opus 5.5 (`claude-opus-5-5`)
- Branch / PR: `nofil-phase3-recommendation-agent`

## Prompts

1. "Give the current status of the program, what's left to do, and how much of the project requirements we have completed."
2. "OK then, build item 7 as it's critical."

## What the assistant produced

- `agent-service/recommendation_agent/`: gRPC server with the v1 API and
  health checks; catalog client; four tools (`list_catalog`, `get_products`,
  `search_catalog`, `recommend`); Hugging Face client through the
  OpenAI-compatible router; agent loop with step limit, time budget, output
  guardrails, decision cache and v1 fallback; JSON decision records with token
  cost, optionally stored in Cosmos DB.
- 19 pytest tests using a scripted fake model and an in-process gRPC catalog.
- Dockerfile that runs the tests during the build; `docker-compose.v2.yml`
  override to run v2 in the local stack.

## Verification

- `pytest`: 19 passed. One test initially failed and exposed a real gap (a
  model reply arriving after the deadline was accepted); the agent now
  re-checks the deadline after every model call.
- v2 running in the local Docker stack without a token: smoke test 4/4, and
  each request logged a decision record (`outcome: fallback`).
- Not yet run against a real model: needs a Hugging Face token (item 8).

## Human review and changes

<To be completed by the reviewer.>
