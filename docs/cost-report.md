# Cost report: v1 vs v2

Cost per request and total cost of `recommendationservice` v1 (random picks)
and v2 (AI agent on Groq), from the canary run of 2026-11-16
([canary-results.md](canary-results.md)). All numbers were read from Azure
Cost Management, Azure Monitor and Log Analytics. No extra load was run for
this report.

## What we actually paid

| Item | Billed |
|---|---|
| Azure, month to date (Cosmos DB, Log Analytics, Container Apps) | **$0.00** (Cost Management, billed in CAD) |
| Groq model calls | **$0.00** (Groq Free plan, no payment method) |
| GitHub Actions and GHCR | $0.00 (free for public repositories) |

The bill is $0 because every service stayed inside a free allowance:
- **Container Apps:** 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million
  requests per subscription per month. By our estimate (11 containers at
  0.25 vCPU for about 100 minutes), the whole shop used about 10% of the vCPU
  grant on the canary day.
- **Cosmos DB:** free tier.
- **Log Analytics:** capped at 0.15 GB per day, under the free 5 GB per month.
- **Groq:** Free plan.

The budget is $10 per month, with alerts at 50%, 80% and 100%. It was set
before the first deployment.

## What it would cost without free allowances

To compare v1 and v2 fairly, we price their usage at list prices.

**List prices** (Azure Retail Prices API for Canada Central, and Groq's model
page; checked 2026-11-16, in USD):

| Resource | Price |
|---|---|
| Container Apps vCPU (active) | $0.000034 per vCPU-second |
| Container Apps memory (active) | $0.000004 per GiB-second |
| Container Apps requests | $0.40 per million |
| Groq `openai/gpt-oss-20b` input | $0.075 per million tokens |
| Groq `openai/gpt-oss-20b` output | $0.30 per million tokens |

Each revision runs one replica with 0.25 vCPU and 0.5 GiB, so a replica costs
$0.00063 per minute: 15 vCPU-seconds plus 30 GiB-seconds.

**How v1 and v2 are separated.** Tags (`component`, `version`) separate each
service and the resources only v2 uses, such as Cosmos DB. v1 and v2 are two
revisions of the same Container App, and Azure tags apply to the app, not to
a revision, so tags alone cannot split their compute. We split it by each
revision's own usage instead, from Azure Monitor metrics filtered by revision.

**Usage on the canary day**, per revision:
- Replica-minutes come from the Azure Monitor `Replicas` metric.
- Request counts come from the `Requests` metric.
- Tokens come from v2's decision logs.

| | v1 | v2 |
|---|---|---|
| Requests served | 393 | 269 |
| Replica-minutes | 60 | 50 |
| Model calls (the rest were cached decisions) | none | 59 |
| Tokens (input / output) | none | 37,491 / 10,750 |
| Compute | $0.0378 | $0.0315 |
| Requests | $0.0002 | $0.0001 |
| Model | none | $0.0060 |
| **Total** | **$0.038** | **$0.038** |
| **Cost per request** | **$0.000097** | **$0.000140** |

v2 costs about **1.45× v1 per request**, or about 4 cents more per thousand
requests.

## What drives the cost

- **Compute dominates both versions at this load.** One replica stays up
  while it waits for requests, so with only a few requests per minute, most of
  the cost is idle time. More traffic per replica would lower the cost per
  request for both versions. The figures above charge all replica time at the
  active rate, so they are an upper bound.
- **The model adds $0.0000224 per request on average** ($0.000102 per model
  call, about 815 tokens). Only 59 of 269 requests needed a model call; the
  other 210 reused a cached decision for the same product and cart.
- **Without the decision cache**, every request would call the model, and
  the model cost per request would be about 4.5 times higher. At 1 million v2
  requests per month, the model would cost about $22 with the cache rate we
  measured, or about $102 without the cache.
- **The faulty v2** of the rollback test made no model calls (0 tokens), so
  it cost compute only. It was rolled back after 11 requests.
