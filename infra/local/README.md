# Local development stack

Runs the full Online Boutique (11 microservices + Redis) on Docker so the team
can study and test the application before anything is deployed to Azure.
No cloud resources are used.

- All services use the upstream prebuilt images (`v0.10.7`).
- `recommendationservice` is built from `online-boutique/src/recommendationservice`,
  because it is the component we will replace with the AI agent (v2).

## Prerequisites

- Docker Desktop (with Docker Compose v2)
- About 4 GB of free memory

## Run

```bash
cd infra/local
docker compose up -d --build
```

Open http://localhost:8080. If port 8080 is taken, choose another one:

```bash
FRONTEND_PORT=8081 docker compose up -d
```

(or copy `.env.example` to `.env` and edit it).

## Verify

```bash
./smoke-test.sh
```

The smoke test checks the frontend pages and the `ListRecommendations`
contract: at most 5 IDs, every ID exists in the catalog, and no cart item is
returned. These are the same correctness rules v2 must satisfy.

## Run v2 (the AI agent) instead of v1

```bash
docker compose -f docker-compose.yml -f docker-compose.v2.yml up -d --build
```

This also starts Ollama, which serves the Hugging Face model
`Qwen/Qwen3-4B-Instruct-2507` (4-bit) locally for free. The first start
downloads about 2.5 GB, and the stack then needs roughly 6 GB of Docker memory.
CPU inference takes several seconds per recommendation; the agent falls back
to v1 if it runs out of time. To use a hosted API instead, set `MODEL_BASE_URL`,
`MODEL_API_KEY` and `MODEL_NAME` in `.env`.

Switch back to v1 with `docker compose up -d --build recommendationservice`
(add `docker compose -f docker-compose.v2.yml stop ollama` to free its memory).
See [agent-service/README.md](../../agent-service/README.md).

## Generate traffic

```bash
docker compose --profile load up -d loadgenerator
docker compose logs -f loadgenerator
```

The Locust load generator browses products, adds items to the cart and checks
out. Stop it with `docker compose --profile load stop loadgenerator`.

## Stop

```bash
docker compose down        # keep the Redis cart volume
docker compose down -v     # also delete the cart data
```

## Port map

| Service               | Port  | Notes                                   |
|-----------------------|-------|-----------------------------------------|
| frontend              | 8080  | published on the host                   |
| recommendationservice | 8080  | built from source                       |
| productcatalogservice | 3550  |                                         |
| cartservice           | 7070  | uses `redis-cart:6379`                  |
| checkoutservice       | 5050  |                                         |
| currencyservice       | 7000  |                                         |
| paymentservice        | 50051 |                                         |
| shippingservice       | 50051 |                                         |
| emailservice          | 5000  | Kubernetes maps 5000 -> 8080; here 5000 |
| adservice             | 9555  |                                         |
