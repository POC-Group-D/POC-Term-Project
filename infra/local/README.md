# Local development stack

Runs the full Online Boutique (11 microservices + Redis) on Docker, with
either v1 or v2 of `recommendationservice`. No cloud resources are used.

**New here? Follow [Getting started](../../README.md#getting-started-local-free-about-15-minutes)
in the main README.** This page is the reference for the same stack.

Run every command from this folder (`infra/local`), in Git Bash on Windows.

## What runs

| Service | Image |
|---|---|
| frontend | Upstream image plus pictures for the 200-product catalog (built from `/catalog/frontend`) |
| productcatalogservice | Upstream image serving the 200-product catalog (built from `/catalog/productcatalogservice`) |
| recommendationservice | v1: built from `online-boutique/src/recommendationservice`. v2: built from `agent-service/` (with `docker-compose.v2.yml`) |
| ollama + model-init | v2 only: local model server and a one-off job that downloads the model |
| all other services, Redis | Upstream prebuilt images (`v0.10.7`) |

Memory: about 4 GB for v1, about 7 GB for v2 (the model takes about 3 GB).

## Commands

| Task | Command |
|---|---|
| Start with v1 | `docker compose up -d --build` |
| Start with v2 | `docker compose -f docker-compose.yml -f docker-compose.v2.yml up -d --build` |
| Back to v1 from v2 | `docker compose up -d --build recommendationservice` |
| Check it works | `./smoke-test.sh` (expects `4/4 checks passed`; works with v1 or v2) |
| Watch v2 decisions | `./watch-agent.sh` |
| Status | `docker compose -f docker-compose.yml -f docker-compose.v2.yml ps` |
| Logs of one service | `docker compose logs -f recommendationservice` |
| Start the load generator | `docker compose --profile load up -d loadgenerator` |
| Stop the load generator | `docker compose --profile load stop loadgenerator` |
| Stop everything | `docker compose -f docker-compose.yml -f docker-compose.v2.yml --profile load down` |
| Stop everything and delete cart data | add `-v` to the line above |

The shop is at http://localhost:8080 unless `FRONTEND_PORT` is set in `.env`.

The Locust load generator browses products, adds items to the cart and checks
out. With v2 on a CPU model, keep it off: it sends requests faster than the
local model can answer, so most requests will fall back to v1.

## Settings (`.env`)

Copy `.env.example` to `.env` (git-ignored) and change what you need:

| Variable | Default | Purpose |
|---|---|---|
| `FRONTEND_PORT` | `8080` | Port of the shop on your computer |
| `LOAD_USERS`, `LOAD_RATE` | `10`, `1` | Load generator users and spawn rate |
| `MODEL_BASE_URL`, `MODEL_API_KEY`, `MODEL_NAME` | local Ollama | Use a hosted OpenAI-compatible API instead (set all three) |
| `OLLAMA_MODEL` | `qwen3:4b-instruct` | Local model to download and use |
| `AGENT_TIMEOUT_SECONDS`, `MAX_AGENT_STEPS`, `SHORTLIST_SIZE` | `60`, `1`, `12` | Agent limits tuned for CPU; see `agent-service/README.md` |

After changing `.env`, run the start command again.

## v2 on a laptop CPU

The local model handles one request at a time at about 30 prompt tokens per
second, so each new product page takes about 20-40 s. Ollama also keeps
working on a request after the agent has given up on it, so many overlapping
requests (several tabs, the load generator) cause timeouts and fallbacks.
A hosted API answers in about 1-2 s and is planned for the Azure canary.

## Port map (inside the Docker network)

| Service               | Port  | Notes                                   |
|-----------------------|-------|-----------------------------------------|
| frontend              | 8080  | published on the host as `FRONTEND_PORT` |
| recommendationservice | 8080  | v1 or v2                                |
| productcatalogservice | 3550  |                                         |
| cartservice           | 7070  | uses `redis-cart:6379`                  |
| checkoutservice       | 5050  |                                         |
| currencyservice       | 7000  |                                         |
| paymentservice        | 50051 |                                         |
| shippingservice       | 50051 |                                         |
| emailservice          | 5000  | Kubernetes maps 5000 -> 8080; here 5000 |
| adservice             | 9555  |                                         |
| ollama                | 11434 | v2 only                                 |
