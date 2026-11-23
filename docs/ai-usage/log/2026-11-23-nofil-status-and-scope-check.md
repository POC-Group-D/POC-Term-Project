# Status summary and requirements check

- Date: 2026-11-23
- Member: Nofil Siddiqui
- Tools and models:
  - Claude Code desktop app, Claude Opus 5.5 (`claude-opus-5-5`)
- Branch: `nofil-azure-v2-groq`

## Prompts

1. "Continue the COEN 6313 project. Read `POC-Term-Project/docs/status.md` first."
2. "Write a summary of everything we have completed, and what is remaining. Go
   through the project requirements to make sure we are aligned with the
   actual project scope."
3. "Yes, fix them" (the three gaps found in step 2).

## What the assistant produced

- `docs/status.md`: a one-page handover (requirements checklist, results,
  deployed state, scripts, what is left).
- A check of every item in `Project_Description-Fall2026_Updated.pdf`
  against the repository. All mandatory requirements are met. It found three
  gaps in how they are documented, fixed here:
  1. **Interface unchanged (Option B) vs. the lecturer's request to redesign
     the API.** `docs/api.md` and the report now explain that the API
     changed once, before the canary, for both versions together. This is
     why a client still cannot tell v1 and v2 apart.
  2. **Separating v1 and v2 costs with tags.** Tags apply to a Container App,
     not to a revision. `infra/azure/README.md`, `docs/cost-report.md` and
     the report now say that v1 and v2 compute is split by each revision's
     Azure Monitor usage.
  3. **Latency compared with v1.** `docs/canary-criteria.md` and the report
     now explain why the p95 threshold judges v2 on its own, and how v1 is
     compared under the same load (the shop-pages p95 per step).

## Verification

- The changes are documentation only; no code or Azure resources changed.
- The report PDF still needs recompiling (Docker was not running).
