# Safely Replacing a Microservice with an AI Agent

COEN 424/6313 Programming on Cloud, Fall 2026, Group D (Option B).

We run Google's [Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo)
online shop (200 products) and replace its recommendation service, the
"You May Also Like" box, with an AI version.

| Version | How it picks "You May Also Like" |
|---|---|
| **v1** (Google's original) | 5 random products the shopper does not already have |
| **v2** (our AI agent) | An AI model (Qwen3-4B from Hugging Face) picks products that go with what the shopper is viewing |

**Team:** Mustafa Ghouri (40355660), Nofil Siddiqui (40292948), Rahil Shah (40329714)

---

## Part 1: Demo on Azure (v1, live)

The shop runs on Azure Container Apps with v1:

**https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io**

1. **Wake it up 5 minutes before the demo.** The apps switch off when nobody
   uses them (so they cost nothing), and the first visit after a pause can take
   1-2 minutes. Run this in Git Bash from the `POC-Term-Project` folder (it
   takes about 3 minutes from cold, then the shop is fast):

   ```bash
   cd infra/azure
   ```

   ```bash
   ./smoke-test.sh https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io
   ```

   Expected last line: `5/5 checks passed` (home page, product page,
   recommendations, add to cart, checkout).

2. **Show the shop.** Open any product and scroll to "You May Also Like":
   these are v1's random picks. Add something to the cart and check out.

3. **Show the Azure resources** (sign in with your Concordia account):
   [resource group `rg-poc-group-d`](https://portal.azure.com/#resource/subscriptions/30bf2f60-c2e2-40c7-9504-001b63a13a60/resourceGroups/rg-poc-group-d/overview):
   10 container apps, the Container Apps environment, Cosmos DB and Log Analytics.

---

## Part 2: Run everything on your computer (v2 with AI)

This runs the whole shop and the AI model in Docker on your own computer. Free.

### You need

- [Docker Desktop](https://www.docker.com/products/docker-desktop/), running, with **at least 8 GB of memory** (Settings > Resources)
- [Git](https://git-scm.com/downloads). On Windows, type all commands in **Git Bash**
- About 6 GB of free disk space

### Steps

1. Get the code and go to the local folder:

   ```bash
   git clone https://github.com/POC-Group-D/POC-Term-Project.git
   ```

   ```bash
   cd POC-Term-Project/infra/local
   ```

2. Start the shop with the AI (v2). The first run downloads about 5 GB and
   takes 5-15 minutes; after that it starts in seconds:

   ```bash
   ./shop.sh v2
   ```

3. Open **http://localhost:8080** and click a product. The AI runs on your
   computer's CPU, so the first time each product takes **20-40 seconds**.
   The "You May Also Like" products now match the product (a Mug gets kitchen
   and coffee items).

4. In a second Git Bash window (in the same `infra/local` folder), watch the
   AI decide:

   ```bash
   ./shop.sh watch
   ```

   One line per recommendation: `AGENT` = the AI chose (with its reason),
   `CACHED` = the same answer reused (same product within 10 minutes),
   `FALLBACK` = the AI failed or was too slow, so v1's random answer was used.

5. When you are done, stop everything (frees about 7 GB of memory):

   ```bash
   ./shop.sh stop
   ```

### Other commands

| Command | What it does |
|---|---|
| `./shop.sh v1` | Run the shop with v1 instead (fast, random picks), to compare |
| `./shop.sh test` | Check that the shop works (expects `4/4 checks passed`) |
| `./shop.sh status` | List the running containers |

### If something goes wrong

| Problem | Fix |
|---|---|
| `Docker is not running` | Start Docker Desktop and wait for "Engine running" |
| `port is already allocated` | Port 8080 is taken: run `cp .env.example .env`, set `FRONTEND_PORT=8081` in `.env`, start again, and open http://localhost:8081 |
| `No such file or directory` | You are not in `POC-Term-Project/infra/local`, or not using Git Bash |
| Pages wait 20-40 s with v2 | Normal: the AI runs on your CPU. Open one product at a time |

---

## More detail

- [agent-service/README.md](agent-service/README.md): how the AI agent works
- [infra/local/README.md](infra/local/README.md): the local Docker setup
- [infra/azure/README.md](infra/azure/README.md): the Azure deployment and costs
- [docs/roadmap.md](docs/roadmap.md): project plan and progress
- [CONTRIBUTING.md](CONTRIBUTING.md): branches, pull requests, secrets and cloud costs
