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
  ├─ prompt: shopper's products + candidate products (from productcatalogservice)
  ├─ model loop (max 4 steps, time budget, capped by the caller's gRPC deadline)
  │    model ──► get_products / search_catalog (optional) ──► productcatalogservice
  │    model ──► recommend(product_ids, reason)
  │
  ├─ guardrails: keep only real catalog ids, drop the shopper's own products,
  │  dedupe, limit 5, top up with random products to match v1's response size
  │
  └─ any error, timeout or no valid ids ───────────────────► v1 random ("fallback")
```

The model must call tools to decide; v2 never just rephrases v1's output.

### Context and tools

Before the first model call the agent reads the catalog
(`ProductCatalogService.ListProducts`, cached 60 s) and builds a bounded
prompt, whatever the catalog size (200 products, see `/catalog`):

- the shopper's products with descriptions
- the store's categories with product counts
- a shortlist (`SHORTLIST_SIZE`, default 20) of products sharing the most
  categories with the shopper's products, topped up with a category-balanced
  sample

Products are written as compact `- id: name (categories)` lines, about half
the tokens of JSON. The model can answer from the shortlist in one call, or use
tools first:

| Tool | Backend call | Purpose |
|---|---|---|
| `browse_category` | catalog cache | All products in one category (up to 40) |
| `get_products` | catalog cache | Descriptions of specific products |
| `search_catalog` | `ProductCatalogService.SearchProducts` | Keyword search; returns a hint when nothing matches |
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

## Model providers

The client speaks the OpenAI chat completions API, so the provider is chosen
purely by configuration:

| Provider | `MODEL_BASE_URL` | `MODEL_NAME` | Cost |
|---|---|---|---|
| Local Ollama (default in `docker-compose.v2.yml`) | `http://ollama:11434/v1` | `qwen3:4b-instruct` (Hugging Face `Qwen/Qwen3-4B-Instruct-2507`, 4-bit) | Free; CPU inference, seconds per request |
| GitHub Models (free tier, rate limited) | `https://models.github.ai/inference` | e.g. `openai/gpt-4o-mini` | Free within daily limits |
| Hugging Face Inference Providers | `https://router.huggingface.co/v1` | `Qwen/Qwen3-4B-Instruct-2507` | Pre-paid credits; the free account had none |

### Measured: local Qwen3-4B on CPU (2026-10-24, 200-product catalog)

Ryzen 7 8840HS, 16 threads, no GPU; settings from `docker-compose.v2.yml`
(`MAX_AGENT_STEPS=1`, `SHORTLIST_SIZE=12`); one request at a time.

| Shopper has | v2 recommended |
|---|---|
| Mug | Nonstick Frying Pan, Travel Coffee Mug, Kitchen Scale, Gooseneck Kettle, Silicone Spatula |
| French Press | Espresso Cups, Travel Coffee Mug, Whole Bean Coffee, Coffee Canister, Ceramic Teapot |
| Yoga Mat | Adjustable Dumbbells, Kettlebell, Foam Roller, Fitness Tracker Band, Resistance Bands |
| Rain Jacket | Trench Coat, Windbreaker, Denim Jacket, Quilted Vest, Wool Overcoat |

| Metric | Result |
|---|---|
| Decided by the model | 4 / 4, no random top-ups |
| Prompt tokens | about 690 per request |
| Latency | 22-39 s per request (one model call) |
| Cost | $0 (local) |

Lessons from tuning on CPU (about 30 prompt tokens/s):

- With 4 steps and a 20-item JSON shortlist (about 1,300 prompt tokens), every
  request timed out: one call took about 35 s and the model usually wanted a
  second one.
- Ollama keeps working on a request after the caller gives up, so timed-out
  requests queue up and slow everything behind them. Avoid overlapping
  requests when running locally.
- A hosted API runs the same prompts in about 1-2 s per call, so the full
  multi-step loop (browse, search, then recommend) is the configuration for
  the Azure canary. At Hugging Face list prices for this model ($0.01 / $0.03
  per million tokens) a request would cost about $0.00001.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `PRODUCT_CATALOG_SERVICE_ADDR` | required | e.g. `productcatalogservice:3550` |
| `PORT` | `8080` | |
| `MODEL_BASE_URL` | empty | OpenAI-compatible endpoint. Without it every request uses the fallback. |
| `MODEL_API_KEY` | empty | **Secret**: Container Apps secret or local `.env`, never in git. Not needed for Ollama. |
| `MODEL_NAME` | `qwen3:4b-instruct` | Any chat model with tool calling on that endpoint |
| `MODEL_MAX_TOKENS` | `300` | Per model call |
| `MODEL_INPUT_PRICE_PER_MTOK`, `MODEL_OUTPUT_PRICE_PER_MTOK` | `0` | USD per million tokens, for cost per request (0 for local inference) |
| `MAX_RECOMMENDATIONS` | `5` | Same as v1 |
| `MAX_AGENT_STEPS` | `4` | `1` = decide in one call from the shortlist (used for local CPU inference) |
| `SHORTLIST_SIZE` | `20` | Candidates in the prompt; the rest are reachable through tools |
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
