# Roadmap

Project plan in dependency order. Tick an item when its PR is merged and note
the owner. Items marked **$** create billable cloud resources and need team
agreement first.

## Done before Phase 1

- [x] D1: group registered, Option B chosen
- [x] D2: presentation (scope: Azure Container Apps, `recommendationservice` as AI agent, Hugging Face model, canary 10/25/50/100, GitHub Actions)
- [x] GitHub organization and repositories created

## Phase 1: Setup (no cloud cost)

- [x] 1. Choose the repo of record: `POC-Term-Project` (Nofil)
- [x] 2. Working conventions: branching, PR/issue templates, AI-usage log (Nofil)
- [x] 3. Run Online Boutique locally on Docker, with a smoke test of the recommendation contract (Nofil)

## Phase 2: Azure foundation

- [x] 4. Resource group `rg-poc-group-d`, $10/month budget with alerts at 50/80/100%, tag scheme (`project`, `component`, `version`) (Nofil)
- [x] 5. v1 on Azure Container Apps, live at https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io (10 apps, internal gRPC, public frontend, 200-product catalog; smoke test 5/5) (Nofil)
- [x] 6. NoSQL store: free-tier Cosmos DB (`recommendations` / `agent-decisions`, West US 2, 1000 RU/s cap) deployed; v2 writes to it once v2 is on Azure (Nofil)

## Phase 3: v2 AI agent

- [x] 7. `agent-service/`: same `ListRecommendations` API, catalog tools, model selects products, guardrails, v1 fallback, 23 unit tests (Nofil). Store extended to 200 products (`/catalog`) so recommendations are meaningful
- [x] 8. Model: Hugging Face free account has no Inference Providers credits, so v2 runs `Qwen/Qwen3-4B-Instruct-2507` locally via Ollama (22-39 s on CPU), and Groq Free `openai/gpt-oss-20b` on Azure (5/5 model decisions, p95 924 ms) (Nofil)
- [x] 9. Per-request telemetry for both versions: v2 records every decision in Cosmos DB (latency, outcome, tokens); requests and errors of both revisions come from Azure Monitor (Nofil)
- [x] 10. Correctness checker: `infra/azure/canary_check.py`, run by `./canary.sh measure` after 5 minutes of load (Nofil)

## Phase 4: Canary

- [x] 11. Criteria table (availability, p95 latency, correctness, cost), fixed before the first canary: [canary-criteria.md](canary-criteria.md) (Nofil)
- [x] 12. Facade: v1 and v2 as labelled revisions of one Container App with weighted traffic (`infra/azure/canary.sh`) (Nofil)
- [x] 13. Canary scripts: 10 -> 25 -> 50 -> 100 with automatic rollback (`./canary.sh run`) (Nofil)
- [ ] 14. Azure Monitor dashboard comparing v1 and v2

## Phase 5: Extra feature

- [ ] 15. GitHub Actions: build and push images to GHCR: done (`.github/workflows/images.yml`, 3 public images); deploying a new revision still to do

## Phase 6: Experiments

- [x] 16. Canary runs with the load generator; one promotion and one fault-injected rollback: [canary-results.md](canary-results.md) (Nofil)
- [ ] 17. Cost per request and total cost for v1 and v2; latency and correctness comparison

## Phase 7: Deliverables

- [ ] 18. D3 progress slides (if still outstanding)
- [ ] 19. D4 report (IEEE, 5-8 pages), presentation, live demo and backup video, source zip
- [ ] 20. Tear down Azure resources
