# GHCR images and first Azure deployment (items 5, 6, 15)

- Date: 2026-10-26
- Member: Nofil Siddiqui
- Tool and model: Claude Code desktop app, Claude Opus 5.5 (`claude-opus-5-5`)
- Branch / PR: `nofil-ghcr-images-and-azure-v1`

## Prompts

1. "This was our initial plan, review the code and see where we stand right now."
2. "Next: publish our images to GHCR (start of item 15) and deploy v1 + Cosmos DB to Azure (items 5-6). Ask me before anything costs money."
3. "Yes, deploy the 15 resources to Azure for Students."

## What the assistant produced

- `.github/workflows/images.yml`: builds `recommendationservice-v2`,
  `productcatalogservice-200` and `frontend` and pushes them to
  `ghcr.io/poc-group-d` with `sha-`, branch and (on `main`) `latest` tags.
- `infra/azure`: deploy uses our GHCR images for the frontend and catalog;
  environment created in `WorkloadProfiles` mode; Cosmos DB region setting.

## What happened

- First workflow run: `productcatalogservice` failed with `write_package`
  denied, because the org already had a package of that name published
  outside this repo (tag `v1`). Ours was renamed `productcatalogservice-200`;
  the existing package was left untouched. All three images are public.
- First deploy: the environment was created in the new default *Express*
  mode, which rejects HTTP/2 ingress and sidecars, so 9 of 10 apps failed.
  Cosmos DB also failed: no capacity in Canada Central. The empty partial
  resources were removed and the template now sets
  `environmentMode: 'WorkloadProfiles'`.
- Second deploy: blocked by an Azure for Students "Allowed locations" policy
  (Central US is not allowed). The usable regions are `canadacentral` and
  `westus2`, so Cosmos DB moved to West US 2.
- Third deploy: succeeded. Smoke test on the live URL 5/5 (pages,
  recommendations, cart, checkout); 200 products and pictures served; Cosmos
  DB free tier with a 1000 RU/s cap; all resources tagged; spend $0.

## Human review and changes

<To be completed by the reviewer.>

## Follow-up: demo-ready README

Prompt: "Break the README into two sections: one to demo the Azure service, and one to run everything locally with Docker and the AI model. Keep it simple: commands I can type to run the pipeline."

- `infra/local/shop.sh`: one command per task (`v2`, `v1`, `watch`, `test`,
  `status`, `stop`); checks Docker is running and prints the shop URL.
- `README.md` rewritten: Part 1 Azure demo (live URL, warm-up, portal link),
  Part 2 local v2 with AI (5 steps), short troubleshooting.
- Verified as written: Azure smoke test 5/5 (about 3 minutes from cold,
  so the README says to warm up 5 minutes early); `./shop.sh v2` started all
  12 containers; a product page took 31 s with an `AGENT` decision and was
  instant on repeat (`CACHED`); `./shop.sh test` 4/4; switching to v1 and
  back worked.
