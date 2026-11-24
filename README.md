# Safely Replacing a Microservice with an AI Agent

COEN 424/6313 Programming on Cloud, Fall 2026, Group D (Option B).
Team: Mustafa Ghouri (40355660), Nofil Siddiqui (40292948), Rahil Shah (40329714)

We run Google's Online Boutique, an online shop with 200 products, and replace
its recommendation service (the "You May Also Like" box under each product)
with an AI version. A canary moves shoppers to the AI version step by step,
and rolls back automatically if it misbehaves.

## The five demos

| Demo | Where | What you show | Time |
|---|---|---|---|
| **1** | Your laptop (Docker) | **v1:** "You May Also Like" shows 5 random products | 2 min |
| **2** | Your laptop (Docker) | **v2:** an AI model picks related products | 3 min |
| **3** | Azure (cloud) | **v1** on Azure: the same shop in the cloud | 3 min |
| **4** | Azure (cloud) | **v2** on Azure (AI on Groq), and moving traffic between v1 and v2 by hand | 4 min |
| **5** | Azure (cloud) | **Automatic canary:** the promotion results, a live automatic rollback, and the monitoring dashboard | 8 min |

Commands are typed in **Git Bash** (Windows). Demos 1-2 run from
`POC-Term-Project/infra/local`, Demos 3-5 from `POC-Term-Project/infra/azure`.
To open Git Bash in a folder: in File Explorer, right-click the folder and
choose **Open Git Bash here**.

---

## Before class (checklist)

Do these in order. Steps 1-3 can be done the day before.

1. **Docker Desktop** is open and shows "Engine running" (Settings > Resources: at least 8 GB memory).
2. **Download the local AI model once** (about 2.5 GB, 5-15 minutes). In `infra/local`:

   ```bash
   ./shop.sh v2
   ```

   Wait for `Ready: ...`, open 2-3 products in the browser (so they are cached and instant in class), then:

   ```bash
   ./shop.sh stop
   ```

3. **Sign in to Azure** with your Concordia account:

   ```bash
   az login
   ```

4. **15 minutes before class, turn the cloud shop on.** In `infra/azure`:

   ```bash
   ./cloud.sh start
   ```

   then wake it up and check it (about 3 minutes):

   ```bash
   ./smoke-test.sh https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io
   ```

   It must end with `5/5 checks passed`.

5. **Check the canary is ready:**

   ```bash
   ./canary.sh status
   ```

   You should see `v1 ... 100` and `v2 ... 0`. If not, run `./canary.sh rollback`.

6. **Open these browser tabs:**
   - Local shop: http://localhost:8080 (it works once Demo 1 starts)
   - Azure shop: https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io
   - [Azure portal: resource group rg-poc-group-d](https://portal.azure.com/#resource/subscriptions/30bf2f60-c2e2-40c7-9504-001b63a13a60/resourceGroups/rg-poc-group-d/overview) (signed in)
   - The canary dashboard: run `./dashboard.sh` in `infra/azure` and open the link it prints
   - [docs/canary-results.md](docs/canary-results.md) on GitHub (the recorded promotion)

> **Cost:** the cloud shop costs credit only while it is on. Turn it off right
> after class (see [After class](#after-class-checklist)). Groq is free.

---

## Demo 1: Local shop, random recommendations (v1)

In Git Bash, in `infra/local`:

1. Start the shop:

   ```bash
   ./shop.sh v1
   ```

   **You should see:** `Ready: http://localhost:8080   Recommendations: v1 (random recommendations)`

2. Open http://localhost:8080 and click **Mug**. Scroll to **"You May Also Like"**.

   **You should see:** 4 random products, e.g. a Canvas Tote Bag next to a Mug,
   each with a grey line such as *From our accessories collection*.

   **Say:** "This is v1, Google's random recommender, moved to our redesigned
   recommendation API: the shop asks for 4 products, and each comes back with a
   reason. v1 has no AI, so its reason is just the product's category."

---

## Demo 2: Local shop, AI recommendations (v2)

Still in `infra/local`:

1. Switch to the AI version:

   ```bash
   ./shop.sh v2
   ```

   **You should see:** `Ready: http://localhost:8080   Recommendations: v2 (Ollama)`

2. Open a **second** Git Bash window in `infra/local` and start the AI log:

   ```bash
   ./shop.sh watch
   ```

3. In the browser, open **Mug** again (wait about 30 seconds after step 1 first).

   **You should see:** related products (coffee and kitchen items), each with
   the AI's own reason under it. The AI log prints a line such as:

   ```
   AGENT     42.4 s | model: qwen3:4b-instruct | tools: ['recommend'] | tokens: 784 | These kitchen items complement the mug...
   ```

   **Say:** "Same shop, same API, but now an AI model (Qwen3-4B from Hugging
   Face) chooses the products, and gives its reason. It runs on my laptop's
   processor, so it is slow (20-60 s). On Azure we use a hosted model that
   answers in under a second."

   `CACHED` in the log means the AI's answer for the same product was reused (10 minutes).

4. Stop the local shop (press **Ctrl+C** in the AI log window first):

   ```bash
   ./shop.sh stop
   ```

---

## Demo 3: Azure (cloud), random recommendations (v1)

In Git Bash, in `infra/azure` (the shop is already on from the checklist):

1. Open https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io
   and click **Mug**.

   **You should see:** random products, like Demo 1. Add something to the cart and check out.

   **Say:** "This is the same shop on Azure Container Apps: 10 microservices,
   one Container App each, talking over gRPC."

2. In the Azure portal tab (resource group **rg-poc-group-d**), show:
   - the 10 **Container Apps** (the shop's services),
   - **Cosmos DB** (the NoSQL database where v2 stores its decisions),
   - **Log Analytics** (logs), and the **budget** ($10/month with alerts).

---

## Demo 4: Azure, AI recommendations (v2) and moving traffic by hand

v1 and v2 run side by side as two versions (revisions) of the recommendation
service. Azure sends each request to one of them, by the share we set. The
shop cannot tell which one answered.

1. Send all recommendation requests to v2:

   ```bash
   ./canary.sh 100
   ```

   **You should see:** `Traffic: v1 0%, v2 100%`

2. Open a **second** Git Bash window in `infra/azure` and start the AI log:

   ```bash
   ./canary.sh watch
   ```

3. Open the [Mug on the Azure shop](https://frontend.blueflower-54b52d82.canadacentral.azurecontainerapps.io/product/6E92ZMYYFZ).

   **You should see:** coffee items in about a second, each with the AI's
   reason, e.g. *Gooseneck Kettle: Perfect for brewing with your mug*. The AI
   log prints:

   ```
   AGENT      0.6 s | model: openai/gpt-oss-20b | tokens: 800 | Complementary coffee accessories for your mug
   ```

   The first product after switching can take a few seconds while v2 wakes up.

   **Say:** "v2 now runs on Azure. The model is `gpt-oss-20b` on Groq's free
   plan; every decision is stored in Cosmos DB."

   **Show the API change:** open [docs/api.md](docs/api.md). **Say:** "We
   redesigned the recommendation API: the caller sends `max_results`, and the
   response carries a `reason` per product. The change only adds fields, so
   old clients still work. Both v1 and v2 implement it, so the canary still
   compares two services with the same API."

4. Split the traffic:

   ```bash
   ./canary.sh 50
   ```

   Refresh the Mug page a few times: **about half** the refreshes show coffee
   items (v2), the others show random products (v1).

5. Roll back:

   ```bash
   ./canary.sh rollback
   ```

   **You should see:** `Traffic: v1 100%, v2 0%`. Refreshing shows random products again.

   **Say:** "This traffic split is the facade of the strangler pattern. Next,
   the canary does this automatically."

6. Press **Ctrl+C** in the AI log window.

---

## Demo 5: Automatic canary (promotion, rollback, dashboard)

The canary sends v2 a growing share of traffic: **10% → 25% → 50% → 100%**.
At each step, simulated shoppers (the Online Boutique load generator) use the
shop, then four rules are checked ([criteria table](docs/canary-criteria.md)):

| Rule | v2 must have |
|---|---|
| Availability | at most 1% errors |
| Latency | 95% of answers within 2 seconds |
| Correctness | at least 95% real AI picks (valid products, none from the cart, a reason for each) |
| Cost | at most 1500 tokens per AI call, Azure spend under $8 |

All pass: go to the next step. Any fails: all traffic goes back to v1.

1. **Start the live rollback first** (it takes about 7 minutes, so talk over it).
   Deploy a **faulty v2**: its Groq key is wrong, so it can never reach the AI:

   ```bash
   ./canary.sh deploy faulty
   ```

   **You should see:** `Traffic: v1 100%, v2 0%`. Then start the canary with 2-minute steps:

   ```bash
   MEASURE_MINUTES=2 ./canary.sh run
   ```

2. **While it runs, show the promotion we recorded:** open
   [docs/canary-results.md](docs/canary-results.md). In Run 1, the good v2
   passed every rule at 10%, 25%, 50% and 100% and was **promoted**.

3. **Back in Git Bash, the rollback:** after about 7 minutes:

   ```
     PASS  Availability  v2 errors 0.0% (v1 0.0%)
     PASS  Latency       v2 p95 249 ms
     FAIL  Correctness   0% correct
     PASS  Cost          0 tokens per model call
   ROLLBACK: a criterion was violated at 10%.
   ```

   **Say:** "The faulty v2 never returned an error, and it was even faster.
   An error-rate check alone would have promoted it. The correctness check
   caught that it was returning random products, and rolled back to v1
   automatically."

4. **Show the dashboard** (the tab from the checklist; press refresh, time
   range **Last hour**):
   - **Requests per revision:** the traffic split over time
   - **Errors by status code:** all successful (2xx)
   - **Latency:** v2's p95
   - **Correctness:** AI decisions vs fallbacks (the faulty v2 is all fallbacks)
   - **Cost:** tokens per AI call

5. Optionally, show the [cost report](docs/cost-report.md) (v1 vs v2 cost per
   request) and the [data model](docs/data-model.md).

---

## After class (checklist)

In `infra/azure`:

1. Put the good v2 back (at 0% traffic, about 1 minute):

   ```bash
   ./canary.sh deploy
   ```

2. **Turn the cloud shop off** (no compute cost while off):

   ```bash
   ./cloud.sh stop
   ```

3. Check it is off: every app must show `Stopped` and `0`.

   ```bash
   ./cloud.sh status
   ```

> `./canary.sh deploy` uses the `latest` images, which CI builds from `main`.
> To deploy another build, set `IMAGE_TAG` (for example `IMAGE_TAG=sha-<commit>`).

---

## Optional: run the full canary again (about 35 minutes)

Only needed for new results. The shop must be on, and it uses about 35 minutes of shop time:

```bash
./canary.sh run
```

Each step prints four `PASS` lines; it ends with
`PROMOTED: v2 met every criterion at each step and now serves 100% of traffic.`

## Optional: Demo 2 with Groq instead of Ollama

The local shop with Groq choosing (fast). It needs your Groq key saved as
`GROQ_API_KEY=...` in `infra/local/.env`. In `infra/local`:

```bash
./shop.sh groq
```

Then `./shop.sh watch` in a second window, open Mug, and `./shop.sh stop` when done.

---

## If something goes wrong

| Message or problem | Fix |
|---|---|
| `Docker is not running` | Start Docker Desktop and wait for "Engine running" |
| `Port 8080 is already used by another container` | Run `echo FRONTEND_PORT=8081 >> .env` in `infra/local`, start again, and open **http://localhost:8081** |
| `No such file or directory` | You are in the wrong folder (`infra/local` for Demos 1-2, `infra/azure` for 3-5), or not in Git Bash |
| Demo 2 shows random products | Run `./shop.sh status`: it must say `v2 (Ollama)`. Look for `FALLBACK` in `./shop.sh watch` |
| Demo 2: no "You May Also Like" box | The AI service is still starting: wait 30 seconds and refresh |
| Demo 2 page waits 20-60 s | Normal: the AI runs on your processor. Open one product at a time |
| Azure link shows "404" or "not found" | The cloud shop is off: run `./cloud.sh start`, then the smoke test |
| `az: command not found` | Close and reopen Git Bash |
| `Not logged in to Azure` | Run `az login` and sign in with your Concordia account |
| Demo 4 still shows random products | Run `./canary.sh status`: v2 must have the share you set. Look for `FALLBACK` in `./canary.sh watch` |
| `No v2 revision yet` | Run `./canary.sh deploy` |
| Demo 5 fails with `no v2 requests` | Too little traffic reached v2 in 2 minutes. Run `./canary.sh rollback`, then `./canary.sh run` again without `MEASURE_MINUTES=2` |
| The dashboard is empty | Data arrives 2-5 minutes late; refresh, and check the time range |

**Whose Azure account is it?** The repository contains no credentials. Every
Azure script acts as whoever ran `az login`, in that person's own Azure for
Students subscription. The shop above is in Nofil's subscription. A teammate
can deploy their own copy: see [infra/azure/README.md](infra/azure/README.md).

## More detail

| Document | What it covers |
|---|---|
| [docs/canary-criteria.md](docs/canary-criteria.md) | The four canary rules and why |
| [docs/canary-results.md](docs/canary-results.md) | Recorded promotion and rollback runs |
| [docs/cost-report.md](docs/cost-report.md) | Cost per request and total cost, v1 vs v2 |
| [docs/api.md](docs/api.md) | Our recommendation API (version 2): `max_results` and a reason per product |
| [docs/data-model.md](docs/data-model.md) | The shop's data and what v2 adds |
| [agent-service](agent-service/README.md) | How the AI agent works |
| [infra/local](infra/local/README.md) | Local Docker setup |
| [infra/azure](infra/azure/README.md) | Azure setup, scripts and costs |
| [docs/roadmap.md](docs/roadmap.md) | Progress |
| [docs/ai-usage](docs/ai-usage/) | AI-assisted development log |
