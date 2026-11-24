# Project status (as of 2026-11-23)

A one-page handover: what the project is, what is done against each
requirement, how it works, and what is left. Details live in the linked
documents.

## The project in one paragraph

COEN 424/6313, Fall 2026, Group D (Mustafa Ghouri, Nofil Siddiqui, Rahil
Shah), **Option B**. We run Google's **Online Boutique** (11 gRPC
microservices, catalog extended to 200 products in 24 categories) on **Azure
Container Apps**. We replace one component, the **recommendation service**
("You May Also Like"):
- **v1:** Google's random picks.
- **v2:** an **AI agent**. A model (`openai/gpt-oss-20b` on **Groq's free
  plan**) chooses products using catalog tools, and the agent falls back to
  v1's behaviour on failure.

A **canary** moves traffic from v1 to v2 in steps (10 → 25 → 50 → 100%).
Container Apps revision traffic splitting is the strangler facade. Four
criteria are checked at every step, and the canary rolls back automatically
if any fails. After the first demo, the lecturer asked us to design the API
ourselves. We added **recommendation API version 2** (`max_results` and a
reason per product), implemented by both versions.

## Requirements checklist

From `Project_Description-Fall2026_Updated.pdf`.

| # | Requirement | Status | Where |
|---|---|---|---|
| 1 | Cloud platform + platform-specific feature | ✅ Azure Container Apps (revisions, weighted traffic, secrets, scale to zero), Cosmos DB, Azure Monitor | `infra/azure/` |
| 2 | Data model: existing + what v2 adds | ✅ | [data-model.md](data-model.md) |
| 3 | NoSQL store | ✅ Cosmos DB free tier, `recommendations/agent-decisions`, one record per v2 response (cart stays on Redis) | [data-model.md](data-model.md) |
| 4 | v1 microservice + v2 AI agent, same API, strangler canary | ✅ The agent chooses with tools (not a rephraser); both versions implement API version 2; facade = labelled revisions | `agent-service/`, `online-boutique/src/recommendationservice/`, `infra/azure/canary.sh` |
| 4b | Lecturer's feedback: design and change the API ourselves | ✅ API version 2: `max_results`, `recommendations[{product_id, reason}]`; additive and backward compatible; shown by the frontend | [api.md](api.md), `online-boutique/protos/demo.proto` |
| 5 | Cost: budget before deploy, tags, model usage, cost per request, total | ✅ $10/month budget with 50/80/100% alerts; tags; tokens per request; **$0 billed**; at list prices v1 $0.000097, v2 $0.000140 per request | [cost-report.md](cost-report.md) |
| 6 | GitHub repo, no secrets | ✅ Keys only in Container Apps secrets and a git-ignored `infra/local/.env` | this repository |
| — | Vibe coding: prompts and models documented | ✅ One log per working session | [ai-usage/](ai-usage/) |
| — | Criteria table defined in advance (availability, p95, correctness, cost) | ✅ | [canary-criteria.md](canary-criteria.md) |
| — | Canary of at least 3 steps under load; one promotion and one rollback | ✅ Promoted at 10/25/50/100%; a faulty v2 (invalid key) rolled back at 10% | [canary-results.md](canary-results.md) |
| — | Monitoring dashboard | ✅ Azure Monitor workbook | `infra/azure/dashboard.bicep`, `./dashboard.sh` |
| — | Extra feature | ✅ Docker + GitHub Actions CI building 4 images to GHCR | `.github/workflows/images.yml` |
| D1-D3 | Group info, scope slides, progress demo | ✅ Done (D3: Demos 1-3 shown; feedback about the API) | slides in the parent folder |
| D4 | Presentation, live demo with a canary step and a rollback, backup video, IEEE report (5-8 pages), source zip | ⏳ Report complete; slides, video, zip to do | [report/](report/) |

## Key results

- **Canary run 1 (promotion):**

  | v2 share | v2 p95 | Correct | Errors |
  |---|---|---|---|
  | 10% | 840 ms | 100% | 0% |
  | 25% | 1362 ms | 100% | 0% |
  | 50% | 902 ms | 100% | 0% |
  | 100% | 645 ms | 100% | 0% |

  About 800 tokens per model call. 45 of 212 v2 requests needed a model
  call; the cache answered the rest.
- **Canary run 2 (rollback):** the faulty v2 had 0% errors and the fastest
  p95 (249 ms), but 0% correct (all fallbacks). It was rolled back at 10%.
  Only the correctness check caught it, which is the key talking point.
- **After API version 2:** one 2-minute step at 50% passed every criterion
  (p95 658 ms, 100% correct including "a reason per product", 864 tokens).
- **After the code review (2026-11-23):** v2 now records failed requests
  (gRPC errors) and `maxResults`. Redeployed as `v2-1123-1840`; one 2-minute
  step at 50% passed every criterion (v1 21 / v2 19 requests, 0% errors,
  p95 524 ms, 100% correct, 838 tokens per model call, $0.00).
- **Cost:** $0.00 billed (free grants). At list prices v2 is about 1.45× v1
  per request; idle compute dominates both, and the model adds about
  $0.00002 per request with the cache.
- **Local AI (Demo 2):** Qwen3-4B through Ollama on CPU takes 20-60 s per decision.

## What is deployed (Azure for Students, Nofil's subscription)

- **Resource group** `rg-poc-group-d`: 10 Container Apps in Canada Central,
  Cosmos DB (free tier) in West US 2, Log Analytics (capped), the budget, and
  the canary dashboard workbook.
- **Shop:** https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io.
  It is **stopped** between demos (`./cloud.sh start` / `stop`).
- **recommendationservice revisions:** label `v1` =
  `recommendationservice--v1-1116-2130` (our v1 image, API version 2), label
  `v2` = `recommendationservice--v2-1123-1840` (Groq). The split is v1 100%,
  v2 0%. Older revisions have 0% and scale to zero, so they cost nothing.
- **Images:** `ghcr.io/poc-group-d/{recommendationservice-v2,
  recommendationservice-v1, productcatalogservice-200, frontend}`. CI tags
  each build `sha-<commit>`, and builds from `main` also `latest`.

## Code and branch state

- All of the work above is on **`main`** (pull request #4 merged on
  2026-11-23). The merged branches were deleted; `main` is the only branch.
  New work goes on a fresh `nofil-...` branch from `main`.
- CI publishes the `latest` images from `main`, and the scripts deploy
  `latest` by default (`./canary.sh deploy`).
- **Tests:** 33 unit tests for the agent (`agent-service/tests`), run in the
  image build; the local smoke test runs 6 checks.

## How to run things

All demo steps are in the [README](../README.md): a before-class checklist,
Demos 1-5 with what to type, what you should see and what to say, and an
after-class checklist.

| Script | Purpose |
|---|---|
| `infra/local/shop.sh v1`, `v2`, `groq`, `watch`, `stop`, `status` | Local Docker shop |
| `infra/azure/cloud.sh start`, `stop`, `status` | Turn the Azure shop on and off |
| `infra/azure/smoke-test.sh <url>` | Check the shop (5/5) |
| `infra/azure/canary.sh deploy` | Add a v2 revision at 0% |
| `infra/azure/canary.sh deploy faulty` | Add a v2 with an invalid key (rollback demo) |
| `infra/azure/canary.sh deploy v1` | Swap v1 onto our image |
| `infra/azure/canary.sh <0-100>`, `rollback` | Set the traffic split |
| `infra/azure/canary.sh status`, `watch` | Show the split; follow v2's decisions live |
| `infra/azure/canary.sh measure` | Load generator, then the criteria check |
| `infra/azure/canary.sh run` | The full canary with automatic rollback |
| `infra/azure/dashboard.sh` | Create or update the dashboard and print its link |

## Things learned the hard way

- `az containerapp revision copy` starts from the app's **newest** template,
  so settings leak from a previous revision. The scripts set every value
  explicitly.
- Moving a revision label does not move its traffic weight.
  `canary.sh deploy v1` re-applies the split.
- Azure Monitor stamps requests 1-2 minutes late, so the checker waits 3
  minutes and widens its window. Container Apps has no response-time
  metric per revision, so v2's latency comes from its own records.
- Groq Free allows 1000 requests per day and 8000 tokens per minute (about
  10 model calls per minute), so the canary load is 2 simulated shoppers.
- In Git Bash, set `MSYS_NO_PATHCONV=1` (`common.sh` does) or Azure resource
  IDs get turned into Windows paths.
- Each service's generated gRPC stubs must match its Protobuf runtime:
  - v2: `agent-service/genproto.sh`
  - v1: grpcio-tools 1.76
  - frontend: protoc-gen-go v1.34.2 and protoc-gen-go-grpc v1.5.1 in a
    `golang:1.27.0-alpine` container
- No LaTeX or Go is installed locally. The report compiles with the
  `texlive/texlive:latest-medium` Docker image ([report/README.md](report/README.md)).

## What is left

1. **Report:** complete (5 pages, contributions filled in). Proofread once
   and submit `docs/report/D4-report-GroupD.pdf`.
2. **D4 slides** (`D4-presentation-GroupD.pdf/.ppt`): 15 minutes covering
   service, architecture, data model, migration method, criteria, v1-v2
   comparison (cost plus one quality attribute), canary steps, dashboard,
   promote/rollback decisions, extra feature, cost monitoring, what works
   and what doesn't, cloud strengths and limits. Every member presents,
   demos or answers questions.
3. **Backup demo video** of Demos 3-5. It needs the Azure shop on for about
   20-30 minutes; ask before starting.
4. **Rehearse** the live demo from the README once.
5. **Source package** `D4-project-GroupD.zip` (without `.venv` folders or
   `infra/local/.env`).
6. **After grading:** tear down the Azure resources (`infra/azure/teardown.sh`).
7. Optional: re-run the full canary (`./canary.sh run`, about 35 minutes of
   shop time) so `canary-results.md` reflects API version 2. The recorded
   runs predate it; the 50% step after the change passed.

Unknown: the exact D4 date (Week 12 Thursday) and how the remaining work is
split among the team.
