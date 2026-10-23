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
- [ ] 5. **$** Deploy v1 to Azure Container Apps (internal gRPC, public frontend): scripted in `infra/azure`, validated with what-if, not yet deployed
- [ ] 6. **$** NoSQL store: free-tier Cosmos DB for agent data: scripted in `infra/azure`, not yet deployed

## Phase 3: v2 AI agent

- [ ] 7. `agent-service/`: same `ListRecommendations` API, catalog tool call, model selects products, v1 fallback
- [ ] 8. Choose and test the Hugging Face model; confirm free-tier limits
- [ ] 9. Per-request telemetry for both versions: version, latency, status, tokens, cost
- [ ] 10. Correctness checker (valid IDs, no cart items, at most 5, schema)

## Phase 4: Canary

- [ ] 11. Criteria table (availability, p95 latency, correctness, cost), fixed before the first canary
- [ ] 12. Facade: v1 and v2 as revisions of one Container App with weighted traffic
- [ ] 13. Canary scripts: 10 -> 25 -> 50 -> 100 with automatic rollback
- [ ] 14. Azure Monitor dashboard comparing v1 and v2

## Phase 5: Extra feature

- [ ] 15. GitHub Actions: build and push images to GHCR, optionally deploy a new revision

## Phase 6: Experiments

- [ ] 16. Canary runs with the load generator; one promotion and one fault-injected rollback
- [ ] 17. Cost per request and total cost for v1 and v2; latency and correctness comparison

## Phase 7: Deliverables

- [ ] 18. D3 progress slides (if still outstanding)
- [ ] 19. D4 report (IEEE, 5-8 pages), presentation, live demo and backup video, source zip
- [ ] 20. Tear down Azure resources
