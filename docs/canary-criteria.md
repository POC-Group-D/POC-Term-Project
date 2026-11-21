# Canary criteria

Fixed before the first canary run, as the project description requires. At
each traffic step we compare v2 (AI agent) with v1 (random picks) under the
same load. If any threshold is violated, all traffic goes back to v1.

## Criteria table

| Metric | How it is measured | Threshold for v2 | Action when violated |
|---|---|---|---|
| **Availability** (error rate) | Azure Monitor `Requests` metric of `recommendationservice`, split by revision and status code. Errors = 5xx responses and timeouts, divided by all requests to that revision during the step | ≤ 1%, and no more than 1 percentage point above v1 in the same step | Roll back to v1 (`./canary.sh rollback`) |
| **Latency** (p95) | `latencyMs` of every v2 request, stored in Cosmos DB (`agent-decisions`), 95th percentile over the step. For comparison, the load generator also reports the p95 of all shop pages in each step | ≤ 2000 ms | Roll back to v1 |
| **Correctness** | Each v2 record in Cosmos DB is checked: the model made the decision (`outcome: agent`, or `cached`: a recent model decision reused; not a fallback), at most 10 products (the API's cap on `max_results`; the frontend asks for 4), no duplicates, every ID exists in the 200-product catalog, none of the cart items is recommended, and every product has a non-empty reason ([API version 2](api.md)). Correctness = share of v2 requests that pass all checks | ≥ 95% | Roll back to v1 |
| **Cost** | Model: tokens per model call from Cosmos DB (Groq Free plan, so $0 billed; tokens are the usage measure; cached answers use none). Azure: spend in Cost Management against the $10 monthly budget | ≤ 1500 tokens per model call on average, and Azure spend below 80% of the budget ($8) | Roll back to v1 and stop the canary |

## How a canary run works

1. Start with v1 at 100% and record the v1 baseline under the load.
2. Steps: **10% → 25% → 50% → 100%** to v2.
3. At each step, run `./canary.sh measure`: the Online Boutique load
   generator (2 simulated shoppers) runs for **5 minutes**, then
   `canary_check.py` checks the four criteria for that window.
4. All criteria met: promote to the next step. After 100% passes, v2 is
   promoted.
5. Any criterion violated: roll back to v1 (`./canary.sh rollback`) and stop.

**Rollback demo:** deploy v2 with an invalid Groq key. Every request then
falls back to random picks, so correctness drops to 0%, which triggers
the rollback.

## Why these thresholds

- **2000 ms p95:** v2 makes one call to Groq per request. We measured a p95
  of 924 ms locally and 250-930 ms per request on Azure, so 2 s leaves room
  without hiding a slow or stuck model. v1 needs no model, so it is much
  faster. The threshold judges v2 on its own, not against v1's speed.
- **95% correct:** the agent checks its own picks and falls back to random
  products when a check fails, so a wrong answer never reaches the shop. A
  fallback still counts as *not correct* here, because then v2 is not doing
  the job of an AI agent.
- **1500 tokens:** a v2 model call uses about 750 tokens. Twice that means the
  prompt or the model's behaviour has changed.
- **$8 of $10:** matches the 80% budget alert set before the first deployment.

## Limits we accept

- Groq Free has per-minute and per-day request limits. The load per step is
  kept small enough to stay within them (measured limits: 1000 requests per
  day, 8000 tokens per minute, so about 10 model calls per minute).
  Requests over the limit fall back and count against correctness.
- Container Apps reports response time only for the whole app, not per
  revision. For that reason, v2's latency comes from its own records.
