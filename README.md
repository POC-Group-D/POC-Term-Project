# Safely Replacing a Microservice with an AI Agent

COEN 424/6313 Programming on Cloud, Fall 2026, Group D (Option B).

We deploy Google's [Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo)
on Microsoft Azure and replace `recommendationservice` with an AI agent version
behind the same gRPC API. A canary release (10% -> 25% -> 50% -> 100%) moves traffic
from v1 to v2 and rolls back if availability, latency, correctness or cost
criteria are violated.

| Version | Behaviour |
|---------|-----------|
| v1 (microservice) | Returns up to 5 random catalog products that are not in the cart. |
| v2 (AI agent) | Reads the cart, calls the product catalog as a tool, and lets a Hugging Face model choose matching products. Falls back to v1 behaviour on model failure or timeout. |

## Team

- Mustafa Ghouri (40355660)
- Nofil Siddiqui (40292948)
- Rahil Shah (40329714)

## Repository layout

```
agent-service/     v2: AI agent implementation of recommendationservice
docs/              Roadmap, design docs, AI-usage log
  roadmap.md       Project plan and progress tracker
  ai-usage/        Prompts, models and tools used for AI-assisted development
infra/
  local/           Docker Compose stack for local development
  azure/           Bicep templates and scripts for Azure Container Apps
online-boutique/   Upstream Online Boutique (v0.10.7), including v1 and protos/
```

## Quick start (local, no cloud cost)

```bash
cd infra/local
docker compose up -d --build
./smoke-test.sh
```

Then open http://localhost:8080. See [infra/local/README.md](infra/local/README.md).

## Working on this repository

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, pull requests and the
rules for secrets and cloud costs. Progress is tracked in
[docs/roadmap.md](docs/roadmap.md).
