# Phase 1: repository conventions and local Docker stack

- Date: 2026-10-23
- Member: Nofil Siddiqui
- Tool and model: Claude Code desktop app, Claude Opus 5.5 (`claude-opus-5-5`)
- Branch / PR: `nofil-phase1-local-setup`

## Prompts

1. "Clone both repos [in the POC-Group-D organization] ... use this folder path for everything."
2. "Go through these two documents [Project_Description-Fall2026_Updated.pdf, D2-GroupD.pptx] so that you're aware of the context."
3. "List down everything that we need to do in the order that it needs to be done ... list down what we have already done and what we need to do."
4. "Now do Phase 1. Write clean, professional code. Create a branch called 'nofil-(whatever change we made)' ... implement the changes and run with docker and then complete phase 1. If any steps require money, pause and ask me for confirmation first."

## What the assistant produced

- Project roadmap with 20 items across 7 phases (`docs/roadmap.md`).
- `infra/local/docker-compose.yml`: full Online Boutique stack from upstream
  `v0.10.7` images, with `recommendationservice` built from source and an
  optional `load` profile for the Locust load generator.
- `infra/local/smoke_test.py` and `smoke-test.sh`: checks frontend pages and the
  `ListRecommendations` contract (at most 5 IDs, valid catalog IDs, no cart items).
- `README.md`, `CONTRIBUTING.md`, PR and issue templates, this AI-usage log.

## Verification

- `docker compose up -d --build`: all 11 services started.
- `./smoke-test.sh`: 4/4 checks passed.
- Load generator for 45 s: 95 requests, 0 failures, including checkouts and
  order confirmation emails.

## Human review and changes

<To be completed by the reviewer.>
