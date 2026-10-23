# Phase 2: Azure guardrails and Container Apps templates

- Date: 2026-10-23
- Member: Nofil Siddiqui
- Tool and model: Claude Code desktop app, Claude Opus 5.5 (`claude-opus-5-5`)
- Branch / PR: `nofil-phase2-azure-foundation`

## Prompts

1. "Implement phase 2: if you need anything from my end, let me know. Follow free tiers only." (with the Phase 2 plan pasted: budget and tags, v1 on Azure Container Apps, Cosmos DB free tier)
2. "Use nofilsiddiqui2000@gmail.com for budget alerts."
3. "Don't deploy yet."

## What the assistant produced

- `infra/azure/main.bicep` and modules: Log Analytics (daily cap), Container Apps
  environment, 10 Container Apps (internal h2c gRPC, public frontend, Redis
  sidecar in cartservice, scale to zero), free-tier Cosmos DB with a
  1000 RU/s account cap.
- `infra/azure/budget.bicep` and `guardrails.sh`: resource group and $10/month
  budget with alerts at 50/80/100% actual and 100% forecast.
- `deploy.sh` (refuses to run without the budget; `--what-if` preview),
  `scale.sh`, `smoke-test.sh`, `teardown.sh`, and `common.sh`, which pins
  every script to the Azure for Students subscription.

## Actions taken in Azure

- Installed Azure CLI 2.91.0; the member signed in with `az login`.
- The login's default subscription was a university production subscription;
  the assistant switched to `Azure for Students` and added the subscription guard.
- Ran `guardrails.sh`: created `rg-poc-group-d` and the budget (both free).
- Ran `deploy.sh --what-if`: 15 resources to create. Not deployed, per the
  member's instruction.

## Human review and changes

<To be completed by the reviewer.>
