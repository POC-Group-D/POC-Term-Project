# Azure deployment (Phase 2)

Online Boutique v1 on Azure Container Apps, designed to stay inside the free
tiers of an Azure for Students subscription.

**Live shop (deployed 2026-10-26):**
https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io

The shop is kept **off** between demos with `./cloud.sh stop`: internet bots
visit the public address every minute or so, which would otherwise keep apps
awake and use credit. `./cloud.sh start` turns it on (then allow about 3 minutes
for the first request), and `./cloud.sh status` shows whether it is on.

## What gets created

| Resource | Name | Cost |
|---|---|---|
| Resource group | `rg-poc-group-d` (Canada Central) | Free |
| Budget | `poc-group-d-monthly`, $10/month, e-mail at 50/80/100% actual and 100% forecast | Free |
| Container Apps environment | `poc-gd-env` (workload profiles, Consumption profile only) | Free |
| Container Apps | `frontend` (public) and 9 internal gRPC services; `cartservice` runs Redis as a sidecar | Scale to zero; usage counts against the monthly free grant |
| Cosmos DB (NoSQL) | `poc-gd-cosmos-*` / `recommendations` / `agent-decisions` (West US 2) | Free tier, hard-capped at 1000 RU/s |
| Log Analytics | `poc-gd-logs` | Free grant, ingestion capped at 0.15 GB/day |

### Images

| App | Image |
|---|---|
| `frontend` | `ghcr.io/poc-group-d/frontend` (upstream + 200-product pictures) |
| `productcatalogservice` | `ghcr.io/poc-group-d/productcatalogservice-200` (upstream + 200 products) |
| `recommendationservice` | upstream v1 (v2, `ghcr.io/poc-group-d/recommendationservice-v2`, comes with the canary) |
| all others | upstream `v0.10.7` |

Our images are built and published by `.github/workflows/images.yml`.
`deploy.sh` uses tag `latest` (builds from `main`); pin a build with
`IMAGE_TAG=sha-<commit> ./deploy.sh`. The current deployment uses `sha-700051b`.

### Azure for Students constraints (learned while deploying)

- **Environment mode:** new environments default to *Express* mode, which
  rejects HTTP/2 (gRPC) ingress and sidecars. `main.bicep` sets
  `environmentMode: 'WorkloadProfiles'` with only the Consumption profile,
  which supports both and has no fixed cost. The mode cannot be changed on an
  existing environment; it must be recreated.
- **Regions:** two policies apply, and a region must be on both lists, which
  leaves only `canadacentral` and `westus2`.
- **Cosmos DB capacity:** Canada Central refused new Cosmos DB accounts
  ("high demand"), so Cosmos DB runs in West US 2 (`AZ_COSMOS_LOCATION`). The
  agent writes to it in the background, so the distance does not slow requests.

### Staying within the free tier

- **Container Apps:** every app has `minReplicas: 0`, so idle apps cost nothing.
  The monthly free grant (180,000 vCPU-s and 360,000 GiB-s) covers about
  16 hours of the whole shop under load. Beyond that, the full stack costs about
  $0.45/hour in Canada Central, charged to the student credit.
- **Redis:** runs as a sidecar in `cartservice` instead of a managed cache
  (about $16/month). Carts are lost when the app scales to zero.
- **Cosmos DB:** `enableFreeTier` plus `totalThroughputLimit: 1000`, so
  throughput cannot exceed the free amount. Only one free-tier account is
  allowed per subscription; `deploy.sh` skips Cosmos DB if it is already used.
- **Log Analytics:** a daily ingestion cap keeps usage under the 5 GB/month
  free grant.

### Tags

Every resource carries `project=poc-group-d`, `course=coen6313`,
`environment=dev`, plus:

- `component`: the service name, or `platform` / `monitoring`
- `version`: `v1` (recommendationservice), `v2` (agent resources such as Cosmos DB), or `shared`

Filter Cost Analysis by these tags to separate v1 and v2 costs.

## Internal networking

Each service is a Container App whose name matches the upstream service name.
Internal apps use `transport: http2` with plaintext (h2c) gRPC, reachable at
`<app-name>:80` inside the environment. Only `frontend` has external ingress.

## Usage

Prerequisites: [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
and `az login`. All scripts pin the `Azure for Students` subscription (override
with `AZ_SUBSCRIPTION`), so nothing is created in another subscription by
mistake.

```bash
cd infra/azure
./guardrails.sh you@example.com   # 1. resource group + budget (free, run once)
./deploy.sh --what-if             # 2. preview changes, no cost
./deploy.sh                       # 3. deploy (refuses to run without the budget)
./smoke-test.sh                   # 4. check pages, recommendations, cart and checkout
```

Other commands:

```bash
./cloud.sh stop    # turn the shop off between demos (no compute cost); ./cloud.sh start to turn it on
./scale.sh up      # keep every app running (demos, canary runs); billed while on
./scale.sh down    # back to scale-to-zero
./teardown.sh      # delete the whole resource group (asks for confirmation)
```

Settings such as region, budget amount and resource group live in `common.sh`
and can be overridden with environment variables, e.g.
`AZ_BUDGET_AMOUNT=20 ./guardrails.sh you@example.com`.

## Files

| File | Purpose |
|---|---|
| `main.bicep` | Log Analytics, Container Apps environment, the 10 Container Apps, Cosmos DB |
| `modules/container-app.bicep` | One service as a Container App |
| `modules/cosmos.bicep` | Free-tier Cosmos DB account, database and container |
| `budget.bicep` | Monthly budget and alerts |
| `common.sh` | Shared settings and the subscription guard |
