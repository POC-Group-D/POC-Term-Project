# Safely Replacing a Microservice with an AI Agent

COEN 424/6313 Programming on Cloud, Fall 2026, Group D (Option B).
Team: Mustafa Ghouri (40355660), Nofil Siddiqui (40292948), Rahil Shah (40329714)

We run Google's Online Boutique, an online shop with 200 products, and replace
its recommendation service (the "You May Also Like" box under each product)
with an AI version.

## The five demos

| Demo | Where it runs | "You May Also Like" shows |
|---|---|---|
| **Demo 1** | Your computer (Docker) | **v1:** 5 random products that are not in the cart |
| **Demo 2** | Your computer (Docker) | **v2:** products chosen by an AI model (Qwen3-4B from Hugging Face), running in Docker |
| **Demo 3** | Azure (cloud) | **v1:** random products, like Demo 1 |
| **Demo 4** | Azure (cloud) | **v2:** products chosen by an AI model on Groq, with traffic moved between v1 and v2 by hand |
| **Demo 5** | Azure (cloud) | **Automatic canary:** v2 gets 10% → 25% → 50% → 100% while the criteria are checked; a faulty v2 is rolled back automatically |

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

This demo uses Qwen through Ollama on your processor. For the same demo with
a hosted model (fast, about 1 s), see
[Demo 2 with Groq](#optional-demo-2-with-groq-instead-of-ollama) below.

1. Switch the shop to the AI version (the first time, this downloads the AI
   model, about 2.5 GB, and takes 5-15 minutes):

   ```bash
   ./shop.sh v2
   ```

   It ends with: `Ready: http://localhost:8080   Recommendations: v2 (Ollama)`

2. Open a **second** Git Bash window in the same `infra/local` folder (in File
   Explorer, right-click the `infra/local` folder > **Open Git Bash here**), and
   start the AI log:

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

### Optional: Demo 2 with Groq instead of Ollama

This runs the same Online Boutique shop on your computer with Groq choosing
the recommendations. You need Docker Desktop running and a Groq Free key
saved as `GROQ_API_KEY=...` in `infra/local/.env`.

1. Open **Docker Desktop** and wait for the engine to start. Then open
   **Git Bash** in `infra/local` and run:

   ```bash
   ./shop.sh groq
   ```

   Wait for `Ready: http://localhost:8080   Recommendations: v2 (Groq)`.
   The first startup may need to build and download images. Keep this
   terminal open until you see `Ready`.

2. Open a second **Git Bash** in the same folder and run `./shop.sh watch`.
   Leave it open while you use the browser.
3. Open [Mug in the local shop](http://localhost:8080/product/6E92ZMYYFZ) and
   scroll to **You May Also Like**. If the script printed a different port,
   use that port. In the watch window, look for `AGENT` and
   `model: openai/gpt-oss-20b`. `CACHED` means the shop reused a previous
   decision. Click a different product for a fresh model call. `FALLBACK`
   means the shop displayed random picks for that request.
4. When you finish, press **Ctrl+C** in the watch window and run
   `./shop.sh stop` in the first window.

If the browser says **site can't be reached**, check that Docker Desktop is
running, run `./shop.sh status`, and open the URL printed by `./shop.sh groq`
after it reports `Ready`. Use `http://` for the local shop.

---

## Demo 3: Azure (cloud), random recommendations (v1)

The same shop, with v1, running on Azure Container Apps:

**https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io**

The cloud shop is kept **off** between demos, so it uses no credit (internet
bots visit public websites all the time and would otherwise keep it running).
These commands need the Azure CLI and `az login` with your Concordia account.

**Whose Azure account is used?** The repository contains no Azure credentials.
Every Azure script acts as whoever ran `az login` on that computer, in that
person's own "Azure for Students" subscription. The shop at the link above
belongs to Nofil's subscription: only Nofil can turn it on or off, and only
Nofil's student credit pays for it. A teammate who runs the scripts with their
own login works on their own subscription (see
[infra/azure/README.md](infra/azure/README.md) to deploy a separate copy).

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

5. **After the demo, turn it off** (or keep it on and continue with Demo 4):

   ```bash
   ./cloud.sh stop
   ```

   `./cloud.sh status` shows whether it is on or off (`Stopped` and `0` copies = off, no cost).

---

## Demo 4: Azure (cloud), AI recommendations (v2) and canary

The same Azure shop, now with v1 and v2 of the recommendation service running
side by side. Azure decides which version answers each request, by the share
you set. The shop's address does not change, and the shop cannot tell which
version answered.

**Once, before the first Demo 4 (not during class):** save your Groq key as
`GROQ_API_KEY=...` in `infra/local/.env`, then from `infra/azure` run:

```bash
./canary.sh deploy
```

It ends with `Traffic: v1 100%, v2 0%`. Do this again only when v2 changes.

1. Turn the shop on and check it, as in Demo 3 steps 1-2.

2. Send all recommendation requests to v2:

   ```bash
   ./canary.sh 100
   ```

   It prints `Traffic: v1 0%, v2 100%`.

3. Open a **second** Git Bash window in `infra/azure` and start the AI log:

   ```bash
   ./canary.sh watch
   ```

4. Open the [Mug on the Azure shop](https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io/product/6E92ZMYYFZ).
   "You May Also Like" now shows related products (coffee and kitchen items),
   in about a second. The AI log prints each decision, for example:

   ```
   AGENT      0.8 s | model: openai/gpt-oss-20b | tokens: 760 | <the model's reason>
   ```

   The first product after switching can take a few seconds while v2 starts.

5. **Canary step and rollback.** Send only part of the traffic to v2, then
   roll back:

   ```bash
   ./canary.sh 50
   ```

   ```bash
   ./canary.sh status
   ```

   About half of the product pages now get AI picks, the rest random ones.
   Then send everything back to v1:

   ```bash
   ./canary.sh rollback
   ```

   "You May Also Like" is random again, as in Demo 3.

6. In the Azure portal (link in Demo 3 step 4), open **recommendationservice >
   Revisions and replicas** to show the two versions and their traffic share,
   and the Cosmos DB account **> Data Explorer > recommendations >
   agent-decisions** to show the stored AI decisions (tokens, latency, outcome).

7. **After the demo:** press Ctrl+C in the AI log window, then:

   ```bash
   ./canary.sh rollback
   ```

   ```bash
   ./cloud.sh stop
   ```

---

## Demo 5: Automatic canary with promotion and rollback

The script moves traffic to v2 step by step (10% → 25% → 50% → 100%). At
each step, simulated shoppers use the shop for a few minutes, then the
[canary criteria](docs/canary-criteria.md) are checked: errors, speed
(p95), correctness and cost. If every criterion passes, v2 moves to the next
step. If any fails, all traffic goes back to v1. Our recorded runs are in
[docs/canary-results.md](docs/canary-results.md).

Each step takes about 8 minutes (5 minutes of load, 3 minutes for Azure's
numbers to arrive), so run the full canary **before class** and show its
output. Run the short rollback **live**. All commands are run from `infra/azure`,
with the shop on (Demo 3 steps 1-2).

1. **Promotion (before class, about 35 minutes):**

   ```bash
   ./canary.sh run
   ```

   Each step prints four `PASS` lines; it ends with
   `PROMOTED: v2 met every criterion at each step and now serves 100% of traffic.`
   Keep this window open, or take a screenshot to show in class.

2. **Rollback (live, about 7 minutes):** deploy a faulty v2 (its Groq key is
   invalid, so it can only return random picks), then start the canary with
   2-minute steps:

   ```bash
   ./canary.sh deploy faulty
   ```

   ```bash
   MEASURE_MINUTES=2 ./canary.sh run
   ```

   At the first step (10%), `Correctness` shows `FAIL 0% correct`, and the
   script prints `ROLLBACK: a criterion was violated at 10%.` All traffic is
   back on v1. Point out that `Availability` still passes: the faulty v2
   never returned an error, so only the correctness check caught it.

3. **After the demo,** put the good v2 back (at 0% traffic) and turn the shop off:

   ```bash
   ./canary.sh deploy
   ```

   ```bash
   ./cloud.sh stop
   ```

---

## If something goes wrong

| Message or problem | Fix |
|---|---|
| `Docker is not running` | Start Docker Desktop and wait for "Engine running" |
| `Port 8080 is already used by another container` | Another shop or program is on port 8080. Run `echo FRONTEND_PORT=8081 >> .env`, start again, and open **http://localhost:8081** |
| `No such file or directory` | You are not in `POC-Term-Project/infra/local`, or not in Git Bash |
| Demo 2 shows random products | Check `./shop.sh status` for `v2 (Ollama)` and use `./shop.sh watch` to check for `FALLBACK`. Make sure you opened the address `shop.sh` printed |
| Demo 2: no "You May Also Like" box | The AI service is still starting: wait 30 seconds and refresh |
| Demo 2 page waits 20-60 s | Normal: the AI runs on your processor. Open one product at a time |
| Demo 3 link shows "404" or "not found" | The cloud shop is off: run `./cloud.sh start` in `infra/azure` |
| `az: command not found` | Close and reopen Git Bash (the Azure CLI was installed after it was opened) |
| `Not logged in to Azure` | Run `az login` and sign in with your Concordia account |
| Demo 4 still shows random products | Run `./canary.sh status`: v2 must have the share you set. Look for `FALLBACK` in `./canary.sh watch` |
| `No v2 revision yet` | Run `./canary.sh deploy` once (see Demo 4) |
| Demo 5 fails at 10% with `no v2 requests` | Too little load reached v2 in that step. Run again with `MEASURE_MINUTES=5` |

Other commands: `./shop.sh status` (which version is running, and where),
`./shop.sh test` (checks the shop, expects `4/4 checks passed`).

More detail: [agent-service](agent-service/README.md) (how the AI works),
[infra/local](infra/local/README.md) (local setup),
[infra/azure](infra/azure/README.md) (Azure and costs),
[roadmap](docs/roadmap.md) (progress).
