# Canary results

Runs of `./canary.sh run` on Azure, judged by the
[canary criteria](canary-criteria.md). Load at every step: the Online
Boutique load generator, 2 simulated shoppers for 5 minutes.

## Run 1: promotion (2026-11-16)

v2 revision `recommendationservice--v2-1116-1839` (Groq `openai/gpt-oss-20b`).

| v2 share | Requests v1 / v2 | v2 errors | v2 p95 | v2 correct | Model calls / cached / fallback | Tokens per model call | Shop pages p95 | Result |
|---|---|---|---|---|---|---|---|---|
| 10% | 103 / 11 | 0% | 840 ms | 100% | 8 / 3 / 0 | 822 | 890 ms | Pass |
| 25% | 78 / 29 | 0% | 1362 ms | 100% | 11 / 18 / 0 | 854 | 1300 ms | Pass |
| 50% | 60 / 58 | 0% | 902 ms | 100% | 13 / 45 / 0 | 805 | 1300 ms | Pass |
| 100% | 0 / 114 | 0% | 645 ms | 100% | 13 / 101 / 0 | 799 | 1100 ms | Pass |

**Decision: promoted.** v2 met every criterion at every step. v1 had no
errors either. Azure spend stayed at $0.00 (within the free monthly
Container Apps grant); Groq Free bills nothing.

## Run 2: rollback with an injected fault (2026-11-16)

v2 revision `recommendationservice--v2-faulty-1116-1956`, deployed with
`./canary.sh deploy faulty` (an invalid Groq key).

| v2 share | Requests v1 / v2 | v2 errors | v2 p95 | v2 correct | Model calls / cached / fallback | Result |
|---|---|---|---|---|---|---|
| 10% | 88 / 11 | 0% | 249 ms | **0%** | 0 / 0 / 11 | **Fail** |

**Decision: rolled back to v1 at the first step.** Every v2 request fell back
to random picks, so correctness dropped to 0%.

## Observations

- **Error rate alone would have missed the fault.** The faulty v2 answered
  every request successfully (0% errors, faster than the good v2), because it
  falls back to random picks when the model fails. Only the correctness
  check caught it, as the project description warns.
- **The decision cache carries most of the load.** The load generator visits
  only 9 products, so most v2 answers reuse a recent model decision. Model
  calls stayed at 8-13 per step, well within the Groq Free limits (8000 tokens
  per minute, 1000 requests per day).
- **v2 is slower than v1 but within the threshold.** A model call takes about
  0.5-1.4 s, while v1 answers immediately. The p95 of whole shop pages was
  0.9-1.3 s in every step.
