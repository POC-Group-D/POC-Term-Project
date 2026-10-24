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

## Follow-up: first live model attempt

- The member created a fine-grained Hugging Face token (Inference Providers
  only) and stored it in the git-ignored `infra/local/.env`.
- `Qwen/Qwen2.5-7B-Instruct` is no longer served by any provider; the
  default became `Qwen/Qwen3-4B-Instruct-2507` (cheapest tool-capable model
  listed by the router: $0.01 / $0.03 per million input / output tokens).
- All 4 live requests returned HTTP 402 "no remaining credits": the free
  account has no Inference Providers credits. Nothing was charged. Each
  request fell back to v1 in about 65 ms, which confirmed the fallback path
  end to end.

## Follow-up: local model via Ollama

Prompt: "Implement A now [run a Hugging Face model locally with Ollama], then we might change to B [GitHub Models] later."

- Model settings renamed to provider-neutral `MODEL_BASE_URL`, `MODEL_API_KEY`,
  `MODEL_NAME`, so Ollama, GitHub Models and Hugging Face differ only by config.
- `docker-compose.v2.yml` now starts Ollama 0.13.5 and pulls `qwen3:4b-instruct`
  (Hugging Face `Qwen/Qwen3-4B-Instruct-2507`, 4-bit, 2.5 GB).
- First live run: the model called tools but used multi-word searches that
  never match and never saw the candidate list, so 0/4 answers were usable
  (one timeout). Changes: the agent now pre-fetches the shopper's products and
  the candidate list into the prompt, `list_catalog` was removed, empty searches
  return a hint, and the prompt asks the model to answer directly when it can.
- Final run: 4/4 requests decided by the model with sensible reasons,
  1-2 model calls, 670-1,840 prompt tokens, 15-40 s per request on CPU, $0.
- Tests: 20 passed.

## Follow-up: 200-product catalog

Prompts: "Why is it giving tank top as recommendation for mug?" then "Add more products to the store. Let's do 200."

- `catalog/generate_catalog.py` keeps the 9 upstream products and adds 191
  hand-written products in 17 groups with generated SVG pictures. Thin
  Dockerfiles layer `products.json` and the pictures onto the upstream
  `productcatalogservice` and `frontend` images; no upstream code changed.
- Agent: the prompt now carries the shopper's products, the category list and
  a bounded shortlist of related products (compact text lines, not JSON); new
  `browse_category` tool. 23 tests pass.
- CPU tuning: 4 steps with a 20-item JSON shortlist timed out on every request
  (about 35 s per call, and Ollama keeps processing abandoned requests, which
  queue up). Local defaults are now 1 step, 12-item shortlist, 60 s budget.
- Result: 4/4 live requests decided by the model with relevant picks (Mug ->
  kitchen and coffee items, Yoga Mat -> fitness, Rain Jacket -> outerwear),
  22-39 s each, about 690 prompt tokens, $0.
- The smoke test's page timeout was raised to 60 s because product pages wait
  for v2.
