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
