# v2 on Azure with Groq, and the canary script (items 8, 12, 13)

- Date: 2026-11-16
- Member: Nofil Siddiqui
- Tools and models:
  - OpenAI Codex: Groq model settings (`MODEL_REASONING_EFFORT`,
    `MODEL_TOOL_CHOICE`), `check_groq.py`, `./shop.sh groq`, model tests
  - Claude Code desktop app, Claude Opus 5.5 (`claude-opus-5-5`): review,
    `canary.sh`, Bicep revision mode, Demo 4 in the README
- Branch: `nofil-azure-v2-groq`

## Prompts

1. (Codex) "Verify Groq Free with the existing V2 agent without changing the Ollama demo."
2. (Codex) "Prepare an Azure V2 run with 0% shop traffic, keep the run minimal, and use Azure for Students."
3. (Claude) "Review everything on Git and on my local version, and familiarize yourself with where things stand."
4. (Claude) "Delete the branch created yesterday. We will do V2 again; reuse yesterday's work if it is useful."
5. (Claude) "Build the canary approach. Do not over-engineer; stay within the project requirements. I must be able to demo V2 to the professor from the README, like the other demos."

## What the assistant produced

- `infra/azure/canary.sh`: `deploy` adds a v2 revision (Groq `openai/gpt-oss-20b`,
  one model call per request, decisions to Cosmos DB) next to v1 with 0% traffic;
  `<percent>` and `rollback` set the traffic split by revision label; `status`
  and `watch` show the split and v2's decisions.
- `modules/container-app.bicep` / `main.bicep`: `recommendationservice` uses
  multiple active revisions, so traffic can be split.
- README: Demo 4 (v2 on Azure, one canary step and one rollback); the local
  Groq run moved under Demo 2.
- Removed yesterday's `stage-v2.sh` and `probe_v2.py` (private console check),
  which `canary.sh` replaces.

## Verification

- `check_groq.py`: 5/5 valid responses decided by the model, no fallbacks,
  p95 924 ms (target 2000 ms), 3089 input + 728 output tokens for 5 requests.
- 27 agent unit tests pass; `az bicep build` succeeds; `bash -n canary.sh`.
- Live run on Azure (6. prompt: "yes, but make sure the credits are not
  exceeded"; spend before the run: $0 of the $10 monthly budget): smoke test
  5/5; at v2 100% every decision was `AGENT` (250-930 ms, about 750 tokens);
  at 50% about half the Mug pages showed coffee items and half random items;
  after `rollback` all pages were random again. Cosmos DB held the v2 records
  (`version: v2`, `outcome: agent`). The shop was stopped afterwards.
- `revision copy` takes settings from the app's latest template, so a value
  left by an earlier revision (`CACHE_TTL_SECONDS=0`) carried over;
  `canary.sh` now sets it explicitly.

## Canary criteria table (item 11)

Prompt: "Let's first build the criteria table. After you build it, write in
simple words what you are doing so that I stay in the loop."

The assistant listed the Azure Monitor metrics available for
`recommendationservice`: `Requests` can be split by revision and status code,
but `ResponseTime` cannot be split by revision. Availability therefore comes
from Azure Monitor, and v2 latency, correctness and tokens come from the
Cosmos DB decision records. Result: `docs/canary-criteria.md`.

## Measurements (items 9, 10)

Prompt: "Yes, measurements next."

- Groq Free limits read from the API's response headers: 1000 requests per
  day, 8000 tokens per minute. The load is therefore 2 simulated shoppers.
- `infra/azure/canary_check.py` checks the four criteria for a time window;
  `./canary.sh measure` runs the upstream Online Boutique load generator
  (Locust) for 5 minutes and then the checker.
- Live run at 50% (about 15 minutes of shop time, then stopped): 122 shop
  pages, 0 failed, page p95 960 ms; v1 47 and v2 57 recommendation requests;
  v2 p95 692 ms, 100% correct (14 model calls, 43 cached), 815 tokens per
  model call, Azure spend $0.00. All criteria met.
- Found during the run: Azure Monitor stamps requests 1-2 minutes late, so
  the checker extends its Azure window by 3 minutes (counts then matched the
  57 Cosmos DB records exactly). A quoting bug in the load summary line
  stopped the first run before the check; fixed and the check re-run on the
  same window.

## Canary run and rollback (items 13, 16)

Prompt: "Yes, canary run next."

- `./canary.sh run` steps through 10/25/50/100%, runs `measure` at each step
  and rolls back on the first failed criterion. `./canary.sh deploy faulty`
  deploys v2 with an invalid Groq key for the rollback demo.
- Live run (about 50 minutes of shop time, then stopped): promotion with all
  criteria met at every step, then the faulty v2 was rolled back at 10%
  (correctness 0%, availability still 0% errors). Results:
  `docs/canary-results.md`. README: Demo 5.

## Canary dashboard (item 14)

Prompt: "Yes, dashboard next." Later: "Do not do anything which costs money...
If you have any doubts, ask me."

- `infra/azure/dashboard.bicep` / `dashboard.sh`: an Azure Monitor workbook
  (free). Requests and status codes per revision come from Azure Monitor
  metrics; v2 latency, outcomes and tokens come from v2's console logs in Log
  Analytics (v1 is the upstream image and does not log each request).
- The summary query was checked against the logs first (good v2: 269
  requests, p95 777 ms, 100% AI decisions; faulty v2: 11 fallbacks), then all
  panels were checked in the portal. No shop or load was started for this.

## Cost report (item 17)

Prompt: "Yes, cost report."

Read-only: Azure Cost Management (month to date $0.00), the Azure Retail
Prices API (Container Apps, Canada Central), Groq's model page
($0.075 / $0.30 per million input / output tokens), the Azure Monitor
`Replicas` and `Requests` metrics, and v2's token counts in Log Analytics.
Result: `docs/cost-report.md` (v1 $0.000097 and v2 $0.000140 per request at
list prices; $0 billed).

## Data model

Prompt: "Yes, data model."

`docs/data-model.md`, written from `demo.proto`, the catalog JSON, the Bicep
templates and the agent's telemetry code. It covers the existing data
(products, carts in Redis, orders not stored, currency, ads, session), the
data v2 adds (Cosmos DB decision records, stateless agent context, in-memory
decision cache), and a Mermaid ER diagram.

## Recommendation API version 2 (professor's feedback)

Prompt: "[The professor said] we need to do something with the API interface...
she recommended that we design and change the API interface ourselves in the
recommendation service API." Then: "I'm going to go with your recommendation...
make these changes and then make sure that everything is running on Azure."

- `demo.proto`: `ListRecommendationsRequest.max_results` and
  `ListRecommendationsResponse.recommendations` (`Recommendation {product_id,
  reason}`). Only fields were added, so version 1 clients and servers keep working.
- v2: the `recommend` tool takes `product_reasons`; random picks get v1's
  rule-based reason; `max_results` honoured (default 5, cap 10); 5 new tests
  (32 total).
- v1: Google's recommender on the new API (category as the reason), built
  as `recommendationservice-v1`. Stubs generated with grpcio-tools 1.76 to
  match its protobuf 6 runtime.
- Frontend: built from source; asks for 4 and shows each reason. Go stubs
  generated in a `golang:1.27.0-alpine` container with protoc-gen-go v1.34.2
  and protoc-gen-go-grpc v1.5.1.
- Checked locally: v1 (4 products with category reasons, shop test 4/4), v2
  with Groq (per-product AI reasons, about 800-870 tokens), v2 with Ollama (21-36 s,
  outcome `agent`). Docs: `docs/api.md`; data model, criteria and README updated.
- Azure (about 20 minutes of shop time, then stopped): new frontend, `./canary.sh
  deploy v1` and `./canary.sh deploy`; smoke test 5/5; Mug with v1 showed 4
  products with category reasons, with v2 4 coffee items with AI reasons; one
  2-minute canary step at 50% passed all criteria (v2 p95 658 ms, 100% correct
  including the reason rule, 864 tokens per model call). Fixed afterwards:
  `deploy v1` now re-applies the traffic split after moving the v1 label.
