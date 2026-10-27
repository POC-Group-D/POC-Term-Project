# Contributing

## Repositories

- **POC-Term-Project** (this repo) is the single source of truth for all code,
  infrastructure and documentation.
- **microservices-demo** is an unmodified fork of upstream, kept for reference
  only. Do not commit project work there.

## Branches

- `main` is always deployable. Never commit to it directly.
- Create one branch per change, named `<member>-<short-description>`, for example
  `nofil-phase1-local-setup` or `rahil-azure-budget-alerts`.
- Keep branches small and short-lived; rebase or merge `main` before opening a PR.

## Commits

- Use the imperative mood: `Add canary rollback script`, not `added script`.
- One logical change per commit.
- If an AI assistant helped with the change, log the session in
  [docs/ai-usage](docs/ai-usage/README.md).

## Pull requests

1. Open a PR against `main` using the PR template.
2. Link the roadmap item or issue it addresses.
3. At least one other member reviews and approves before merging.
4. Squash-merge, then delete the branch.

## Secrets

- Never commit API keys, tokens, connection strings or Azure credentials.
- Local values go in `.env` files (git-ignored); commit only `.env.example`.
- Cloud values go in Azure Key Vault or Container Apps secrets.
- If a secret is committed by mistake, rotate it immediately; deleting the
  commit is not enough.

## Cloud costs

- The Azure budget and alerts must exist before the first deployment.
- Tag every Azure resource with `project=poc-group-d`, `component=<service>` and,
  where relevant, `version=v1|v2`.
- Ask the team before creating any paid resource, and delete resources when
  you finish testing.
