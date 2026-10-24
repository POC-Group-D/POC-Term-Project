# recommendationservice v2: AI agent

Drop-in replacement for Online Boutique's `recommendationservice`. It serves
the same gRPC API (`hipstershop.RecommendationService/ListRecommendations`,
generated from `online-boutique/protos/demo.proto`), so the frontend cannot
tell which version answered.

| | v1 (upstream) | v2 (this service) |
|---|---|---|
| Decision | Random products not in the context | A language model chooses, using catalog tools |
| Context used | Only to exclude products | Names, categories and descriptions of the shopper's products |
| On failure | Error | Falls back to v1 behaviour |

## How a request is handled

```
ListRecommendations(user_id, product_ids)
  │
  ├─ cache hit for this context? ──────────────────────────► reuse decision ("cached")
  │
  ├─ model loop (max 4 steps, 8 s budget, capped by the caller's gRPC deadline)
  │    model ──► list_catalog / get_products / search_catalog ──► productcatalogservice
  │    model ──► recommend(product_ids, reason)
  │
  ├─ guardrails: keep only real catalog ids, drop the shopper's own products,
  │  dedupe, limit 5, top up with random products to match v1's response size
  │
  └─ any error, timeout or no valid ids ───────────────────► v1 random ("fallback")
```

The model must call tools to decide; v2 never just rephrases v1's output.

### Tools

| Tool | Backend call | Purpose |
|---|---|---|
| `list_catalog` | `ProductCatalogService.ListProducts` (cached 60 s) | Every product with id, name, categories |
| `get_products` | catalog cache | Details of specific products, e.g. the shopper's |
| `search_catalog` | `ProductCatalogService.SearchProducts` | Keyword search |
| `recommend` | none | Final answer: product ids and a one-sentence reason |

On the last step only `recommend` is offered, so the model must answer.

## Decision record (data model)

Each request produces one record. It is logged to stdout as JSON (collected by
Log Analytics on Azure) and, if configured, written to Cosmos DB
(`recommendations` / `agent-decisions`, partition key `/userId`, 30-day TTL).

| Field | Type | Meaning |
|---|---|---|
| `id` | string (UUID) | Record id |
| `userId` | string | Frontend session id (partition key) |
| `timestamp` | ISO 8601 | When the request was served |
| `version` | `"v2"` | Lets the canary split metrics by version |
| `contextProductIds` | string[] | Products the shopper is viewing or has in the cart |
| `recommendedProductIds` | string[] | What was returned |
| `outcome` | `agent` \| `cached` \| `fallback` | Who decided |
| `fallbackReason` | string | Why the agent fell back (empty otherwise) |
| `reason` | string | The model's one-sentence explanation |
| `toolCalls` | object[] | Tool name and arguments, in order |
| `steps` | int | Model calls made |
| `toppedUp` | int | Random products added to reach 5 |
| `model` | string | Model id, or `none` |
| `promptTokens`, `completionTokens` | int | Model usage for this request |
| `estimatedCostUsd` | number | Tokens × configured prices |
| `latencyMs` | number | Server-side handling time |

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `PRODUCT_CATALOG_SERVICE_ADDR` | required | e.g. `productcatalogservice:3550` |
| `PORT` | `8080` | |
| `HF_TOKEN` | empty | Hugging Face access token. **Secret**: Container Apps secret or local `.env`, never in git. Without it every request uses the fallback. |
| `HF_MODEL` | `Qwen/Qwen3-4B-Instruct-2507` | Any Inference Providers chat model that supports tool calling |
| `HF_BASE_URL` | `https://router.huggingface.co/v1` | OpenAI-compatible endpoint |
| `MODEL_MAX_TOKENS` | `300` | Per model call |
| `MODEL_INPUT_PRICE_PER_MTOK`, `MODEL_OUTPUT_PRICE_PER_MTOK` | `0` | USD per million tokens, for cost per request (set once the provider is chosen) |
| `MAX_RECOMMENDATIONS` | `5` | Same as v1 |
| `MAX_AGENT_STEPS` | `4` | |
| `AGENT_TIMEOUT_SECONDS` | `8` | Overall model budget per request |
| `CACHE_TTL_SECONDS` | `600` | Reuse a decision for the same context; `0` disables (use `0` when measuring model cost per request) |
| `COSMOS_ENDPOINT`, `COSMOS_KEY` | empty | Enables the Cosmos DB sink. `COSMOS_KEY` is a secret. |
| `COSMOS_DATABASE`, `COSMOS_CONTAINER` | `recommendations`, `agent-decisions` | |

## Development

```bash
cd agent-service
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt   # .venv/bin/pip on macOS/Linux
.venv/Scripts/python -m pytest
./genproto.sh                                       # only if demo.proto changes
```

The tests use a scripted fake model and an in-process fake catalog, so they
need no network or token. The Docker build runs them and fails if any fail.

Run v2 inside the local shop (`infra/local`):

```bash
cd ../infra/local
docker compose -f docker-compose.yml -f docker-compose.v2.yml up -d --build
./smoke-test.sh
docker compose logs -f recommendationservice      # one JSON decision record per request
```
