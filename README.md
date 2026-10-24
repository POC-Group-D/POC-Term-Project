# Safely Replacing a Microservice with an AI Agent

COEN 424/6313 Programming on Cloud, Fall 2026, Group D (Option B).

We run Google's [Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo)
and replace its `recommendationservice` with an AI agent behind the same gRPC
API. A canary release (10% -> 25% -> 50% -> 100%) will move traffic from v1 to
v2 on Azure and roll back if availability, latency, correctness or cost
criteria are violated.

| Version | How it chooses "You May Also Like" products |
|---|---|
| v1 (microservice, upstream) | Up to 5 random products the shopper does not already have |
| v2 (AI agent, `agent-service/`) | A language model picks related products, using catalog tools; falls back to v1 on any failure |

The store is extended from 9 to 200 products (`catalog/`) so recommendations are meaningful.

## Team

- Mustafa Ghouri (40355660)
- Nofil Siddiqui (40292948)
- Rahil Shah (40329714)

---

## Getting started (local, free, about 15 minutes)

Everything below runs on your own computer with Docker. No Azure account,
API key or payment is needed.

### 1. Install the prerequisites

| Tool | Notes |
|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Start it and wait until it says "Engine running". In Settings > Resources, give it **at least 8 GB of memory** (v1 alone needs about 4 GB). |
| [Git](https://git-scm.com/downloads) | On Windows this includes **Git Bash**. Use Git Bash for every command below; the `.sh` scripts do not run in PowerShell or cmd. |
| Disk space | About 6 GB (shop images about 2.5 GB, AI model about 2.5 GB) |

### 2. Get the code

```bash
git clone https://github.com/POC-Group-D/POC-Term-Project.git
```

```bash
cd POC-Term-Project
```

The working code is on the `nofil-foundation-and-recommendation-agent` branch until it is merged into `main`:

```bash
git checkout nofil-foundation-and-recommendation-agent
```

All other commands are run from the `infra/local` folder:

```bash
cd infra/local
```

If you open a new terminal later, `cd` back into `POC-Term-Project/infra/local` first.

### 3. (Optional) Choose a port

The shop opens on port 8080. If something else already uses it, create a
`.env` file from the example and change `FRONTEND_PORT` (e.g. to 8081):

```bash
cp .env.example .env
```

`.env` is git-ignored, so your local settings and any keys never get committed.

### 4. Start the shop with v1 (the original)

```bash
docker compose up -d --build
```

The first run downloads the shop images (a few minutes); later runs take seconds.
Open **http://localhost:8080** (or your `FRONTEND_PORT`). You should see the
store with 200 products. Open any product: the "You May Also Like" box at the
bottom shows v1's random picks.

Check that everything works:

```bash
./smoke-test.sh
```

Expected last line: `4/4 checks passed`.

### 5. Switch to v2 (the AI agent)

```bash
docker compose -f docker-compose.yml -f docker-compose.v2.yml up -d --build
```

This also starts **Ollama**, which runs the Hugging Face model
`Qwen/Qwen3-4B-Instruct-2507` on your CPU for free. The first run downloads
the model (about 2.5 GB, a few minutes). `docker compose ps` shows
`model-init` as *Exited (0)* once the download has finished.

Now open a product in the shop. **The page takes about 20-40 seconds** the
first time, because the model is thinking on your CPU. The picks should match
the product (e.g. a Mug gets kitchen and coffee items). Opening the same
product again within 10 minutes is instant (the decision is cached).

### 6. Watch the agent's decisions

In a second Git Bash window (`cd` into `POC-Term-Project/infra/local` first):

```bash
./watch-agent.sh
```

Each recommendation prints one line, for example:

```
AGENT     17.7 s | tools: ['recommend'] | tokens: 780 | These products complement the shopper's mug...
CACHED     0.0 s | tools: [] | tokens: 0 | These products complement the shopper's mug...
FALLBACK   0.1 s | tools: [] | tokens: 0 | APIConnectionError: Connection error.
```

`AGENT` = the model decided, `CACHED` = a recent decision was reused,
`FALLBACK` = the model was unavailable or too slow, so v1's random choice was
returned instead. Press Ctrl+C to stop watching.

To see the fallback, stop the model, open a product you have not opened in the
last 10 minutes, then start the model again:

```bash
docker compose -f docker-compose.yml -f docker-compose.v2.yml stop ollama
```

```bash
docker compose -f docker-compose.yml -f docker-compose.v2.yml start ollama
```

### 7. Switch back to v1, or stop everything

Back to v1 (fast, random):

```bash
docker compose up -d --build recommendationservice
```

Stop everything and free the memory (the model alone uses about 3 GB):

```bash
docker compose -f docker-compose.yml -f docker-compose.v2.yml --profile load down
```

Your downloaded images and model stay on disk, so the next start is quick.

### Troubleshooting

| Problem | Fix |
|---|---|
| `no configuration file provided` or `docker-compose.yml: not found` | You are in the wrong folder: `cd` into `POC-Term-Project/infra/local`. |
| `Cannot connect to the Docker daemon` | Start Docker Desktop and wait for "Engine running". |
| `port is already allocated` | Another app uses the port: set `FRONTEND_PORT` in `.env` (step 3). |
| `./smoke-test.sh: No such file or directory` or `'.' is not recognized` | Use Git Bash, not PowerShell or cmd. |
| Product pages take 20-40 s with v2 | Expected: the model runs on your CPU. |
| Every line in `watch-agent.sh` says `FALLBACK ... timed out` | The CPU is overloaded: close other heavy apps and other Docker stacks, and do not open many product pages at once (the local model handles one request at a time). |
| Containers keep restarting or Docker is very slow | Give Docker Desktop more memory (Settings > Resources). |

---

## Repository layout

```
agent-service/     v2: the AI agent (Python, gRPC); see its README for the design
catalog/           200-product catalog and pictures (thin layers over upstream images)
docs/
  roadmap.md       Project plan and progress tracker
  ai-usage/        Log of AI-assisted development (required by the course)
infra/
  local/           Docker Compose stack used in "Getting started"
  azure/           Bicep templates and scripts for Azure Container Apps (Phase 2)
online-boutique/   Upstream Online Boutique v0.10.7, including v1 and protos/
```

More detail: [infra/local/README.md](infra/local/README.md) (local stack),
[agent-service/README.md](agent-service/README.md) (how the agent works and
its settings), [catalog/README.md](catalog/README.md) (product data),
[infra/azure/README.md](infra/azure/README.md) (Azure, costs money: ask the
team first).

## Working on this repository

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, pull requests and the
rules for secrets and cloud costs. Progress is tracked in
[docs/roadmap.md](docs/roadmap.md).
