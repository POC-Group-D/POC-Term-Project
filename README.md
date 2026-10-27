# Safely Replacing a Microservice with an AI Agent

COEN 424/6313 Programming on Cloud, Fall 2026, Group D (Option B).
Team: Mustafa Ghouri (40355660), Nofil Siddiqui (40292948), Rahil Shah (40329714)

We run Google's Online Boutique, an online shop with 200 products, and replace
its recommendation service (the "You May Also Like" box under each product)
with an AI version.

## The three demos

| Demo | Where it runs | "You May Also Like" shows |
|---|---|---|
| **Demo 1** | Your computer (Docker) | **v1:** 5 random products that are not in the cart |
| **Demo 2** | Your computer (Docker) | **v2:** products chosen by an AI model (Qwen3-4B from Hugging Face), running in Docker |
| **Demo 3** | Azure (cloud) | **v1:** random products, like Demo 1 (connecting the AI on Azure is our next step) |

---

## Before Demos 1 and 2 (once)

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/)
(running, with at least 8 GB of memory in Settings > Resources) and
[Git](https://git-scm.com/downloads). On Windows, type every command in **Git Bash**.

```bash
git clone https://github.com/POC-Group-D/POC-Term-Project.git
```

```bash
cd POC-Term-Project/infra/local
```

All commands for Demos 1 and 2 are run from this `infra/local` folder.

---

## Demo 1: Local shop, random recommendations (v1)

1. Start the shop:

   ```bash
   ./shop.sh v1
   ```

   It ends with: `Ready: http://localhost:8080   Recommendations: v1 (random recommendations)`

2. Open the address it printed and click any product, e.g. **Mug**. Scroll to
   **"You May Also Like"**: the products are random (a Mug can get loafers or a tank top).

---

## Demo 2: Local shop, AI recommendations (v2)

1. Switch the shop to the AI version (the first time, this downloads the AI
   model, about 2.5 GB, and takes 5-15 minutes):

   ```bash
   ./shop.sh v2
   ```

   It ends with: `Ready: http://localhost:8080   Recommendations: v2 (AI recommendations)`

2. Open a **second** Git Bash window, go to the same folder, and start the AI log:

   ```bash
   cd POC-Term-Project/infra/local
   ```

   ```bash
   ./shop.sh watch
   ```

3. Wait about 30 seconds (the AI service is starting), then in the browser open
   the same product as in Demo 1, e.g. **Mug**. The page takes **20-60 seconds**
   (the AI runs on your computer's processor; the first product after starting
   is the slowest). Now "You May Also Like" shows related products, and the AI
   log prints its choice and reason, for example:

   ```
   AGENT     42.4 s | tools: ['recommend'] | tokens: 784 | These kitchen cookware items complement the shopper's existing mug...
   ```

   (Mug in Demo 1: Polo Shirt, Rain Boots, Travel Pillow, Wool Slippers.
   Mug in Demo 2: Silicone Spatula, Coffee Canister, Kitchen Scale, Garlic Press.)

   Opening the same product again is instant (`CACHED`: the AI's answer is reused for 10 minutes).

   **Tip:** open 2-3 products before the demo so you can show them instantly,
   then open one new product live.

When you finish Demos 1 and 2, stop the local shop:

```bash
./shop.sh stop
```

---

## Demo 3: Azure (cloud), random recommendations (v1)

The same shop, with v1, running on Azure Container Apps:

**https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io**

The cloud shop is kept **off** between demos, so it uses no credit (internet
bots visit public websites all the time and would otherwise keep it running).
These commands need the Azure CLI and `az login` with your Concordia account.

1. **10 minutes before the demo, turn it on.** From the `POC-Term-Project` folder:

   ```bash
   cd infra/azure
   ```

   ```bash
   ./cloud.sh start
   ```

2. **Wake it up and check it** (about 3 minutes):

   ```bash
   ./smoke-test.sh https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io
   ```

   It ends with `5/5 checks passed` (home page, product page, recommendations,
   add to cart, checkout). The shop is now fast.

3. Open the link above, click a product: **"You May Also Like"** shows random
   products, like Demo 1. Add a product to the cart and check out.

4. Show the cloud resources in the Azure portal (sign in with your Concordia account):
   [resource group rg-poc-group-d](https://portal.azure.com/#resource/subscriptions/30bf2f60-c2e2-40c7-9504-001b63a13a60/resourceGroups/rg-poc-group-d/overview):
   the 10 shop services (Container Apps), Cosmos DB (database for the AI's decisions) and Log Analytics (logs).

5. **After the demo, turn it off:**

   ```bash
   ./cloud.sh stop
   ```

   `./cloud.sh status` shows whether it is on or off (`Stopped` and `0` copies = off, no cost).

---

## If something goes wrong

| Message or problem | Fix |
|---|---|
| `Docker is not running` | Start Docker Desktop and wait for "Engine running" |
| `Port 8080 is already used by another container` | Another shop or program is on port 8080. Run `echo FRONTEND_PORT=8081 >> .env`, start again, and open **http://localhost:8081** |
| `No such file or directory` | You are not in `POC-Term-Project/infra/local`, or not in Git Bash |
| Demo 2 shows random products | Check `./shop.sh status`: it must say `v2 (AI recommendations)`. Make sure you opened the address `shop.sh` printed |
| Demo 2: no "You May Also Like" box | The AI service is still starting: wait 30 seconds and refresh |
| Demo 2 page waits 20-60 s | Normal: the AI runs on your processor. Open one product at a time |
| Demo 3 link shows "404" or "not found" | The cloud shop is off: run `./cloud.sh start` in `infra/azure` |
| `az: command not found` | Close and reopen Git Bash (the Azure CLI was installed after it was opened) |
| `Not logged in to Azure` | Run `az login` and sign in with your Concordia account |

Other commands: `./shop.sh status` (which version is running, and where),
`./shop.sh test` (checks the shop, expects `4/4 checks passed`).

More detail: [agent-service](agent-service/README.md) (how the AI works),
[infra/local](infra/local/README.md) (local setup),
[infra/azure](infra/azure/README.md) (Azure and costs),
[roadmap](docs/roadmap.md) (progress).
