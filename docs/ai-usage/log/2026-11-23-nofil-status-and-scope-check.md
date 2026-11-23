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

## Code review and fixes

Prompts:

4. "Now, do an independent code review (run and test everything). We will
   complete the report once we have the final code."
5. "Fix all four" (the findings of step 4).

What was run: 32 agent unit tests, `bash -n` on every script, `az bicep
build` on every template, the Compose files, the local shop with v1 and with
v2 on Groq (smoke test and a contract test of API version 2), and two faults:
an invalid Groq key (v2 falls back, valid answers) and a stopped catalog
(gRPC `UNAVAILABLE`).

Findings and fixes:

1. A failed v2 request (non-OK gRPC status) left no decision record, and
   Azure Monitor counts it as HTTP 200, so the availability criterion could
   not see it. v2 now records it (`outcome: error`), and `canary_check.py`
   counts those records as errors.
2. Tokens per model call were averaged over fallbacks too (0 tokens). Now
   only `agent` decisions count.
3. Correctness checked "at most 10 products". Records now carry `maxResults`,
   and the check uses it.
4. The local smoke test did not cover API version 2. It now checks
   `max_results` (4, and 15 capped to 10) and a reason per product: 6 checks.

Verification: 33 unit tests (one new); `canary_check.py` with mocked Azure
data (a healthy step passes; 2 gRPC errors in 41 requests fail availability);
local smoke test 6/6 on v1 and on v2 (Groq); the stopped catalog now leaves an
`error` record. Observation: one empty-cart request got Groq's
`tool_use_failed` (the model did not call `recommend`) and fell back, as
designed.
