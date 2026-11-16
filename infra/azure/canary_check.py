"""Check the canary criteria (docs/canary-criteria.md) for one time window.

Reads v2's decision records from Cosmos DB and the request counts of both
revisions from Azure Monitor, prints one line per criterion, and exits with
0 when every criterion passes and 1 when any fails.

Run by ./canary.sh measure; it passes the window and the revision names.
"""

import argparse
import json
import math
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from azure.cosmos import CosmosClient

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog/productcatalogservice/products.json"

# Thresholds from docs/canary-criteria.md.
MAX_ERROR_RATE = 1.0         # percent
MAX_ERROR_RATE_ABOVE_V1 = 1.0  # percentage points
MAX_P95_MS = 2000
MIN_CORRECT = 95.0           # percent
MAX_TOKENS_PER_REQUEST = 1500
MAX_SPEND = 8.0              # USD, 80% of the $10 budget
MAX_RECOMMENDATIONS = 5


def az(*args):
    out = subprocess.run([shutil.which("az"), *args, "--output", "json"],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out) if out.strip() else None


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def p95(values):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def request_counts(app_id, start, end):
    """{revision: (total requests, failed requests)} from Azure Monitor."""
    # Azure Monitor counts requests per whole minute and stamps them 1-2 minutes
    # late (checked against the Cosmos DB records). Start at the whole minute and
    # end 3 minutes after the load; nothing else calls the service in between.
    start, end = start - start % 60, end + 180
    result = az("monitor", "metrics", "list", "--resource", app_id, "--metric", "Requests",
                "--aggregation", "Total", "--interval", "PT1M",
                "--start-time", iso(start), "--end-time", iso(end),
                "--filter", "revisionName eq '*' and statusCodeCategory eq '*'")
    counts = {}
    for series in result["value"][0]["timeseries"]:
        labels = {m["name"]["value"].lower(): m["value"] for m in series["metadatavalues"]}
        total = sum(point.get("total") or 0 for point in series["data"])
        revision = labels.get("revisionname", "")
        failed = total if labels.get("statuscodecategory", "").startswith("5") else 0
        old_total, old_failed = counts.get(revision, (0, 0))
        counts[revision] = (old_total + total, old_failed + failed)
    return counts


def is_correct(record, catalog_ids):
    ids = record["recommendedProductIds"]
    return (record["outcome"] in ("agent", "cached")
            and 0 < len(ids) <= MAX_RECOMMENDATIONS
            and len(set(ids)) == len(ids)
            and all(i in catalog_ids for i in ids)
            and not set(ids) & set(record["contextProductIds"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True, help="window start, epoch seconds")
    parser.add_argument("--end", type=int, required=True, help="window end, epoch seconds")
    parser.add_argument("--v1", required=True, help="v1 revision name")
    parser.add_argument("--v2", required=True, help="v2 revision name")
    parser.add_argument("--app-id", required=True, help="resource ID of recommendationservice")
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--budget", required=True, help="budget name for the Azure spend")
    args = parser.parse_args()

    catalog_ids = {p["id"] for p in json.loads(CATALOG.read_text(encoding="utf-8"))["products"]}
    container = (CosmosClient(os.environ["COSMOS_ENDPOINT"], credential=os.environ["COSMOS_KEY"])
                 .get_database_client("recommendations").get_container_client("agent-decisions"))
    records = list(container.query_items(
        "SELECT * FROM c WHERE c.version = 'v2' AND c._ts >= @start AND c._ts <= @end",
        parameters=[{"name": "@start", "value": args.start}, {"name": "@end", "value": args.end}],
        enable_cross_partition_query=True))

    counts = request_counts(args.app_id, args.start, args.end)
    v1_total, v1_failed = counts.get(args.v1, (0, 0))
    v2_total, v2_failed = counts.get(args.v2, (0, 0))
    v1_rate = 100 * v1_failed / v1_total if v1_total else 0.0
    v2_rate = 100 * v2_failed / v2_total if v2_total else 0.0

    latency = p95([r["latencyMs"] for r in records])
    correct = 100 * sum(is_correct(r, catalog_ids) for r in records) / len(records) if records else None
    model_calls = [r for r in records if r["outcome"] != "cached"]
    tokens = (sum(r["promptTokens"] + r["completionTokens"] for r in model_calls) / len(model_calls)
              if model_calls else 0.0)
    spend = float(az("consumption", "budget", "show", "--budget-name", args.budget,
                     "--resource-group", args.resource_group,
                     "--query", "currentSpend.amount") or 0)
    outcomes = {o: sum(r["outcome"] == o for r in records) for o in ("agent", "cached", "fallback")}

    print(f"Requests to recommendationservice: v1 {v1_total:.0f}, v2 {v2_total:.0f}. "
          f"v2 decisions: {outcomes['agent']} by the model, {outcomes['cached']} cached, "
          f"{outcomes['fallback']} fallback")
    rows = [
        ("Availability", f"v2 errors {v2_rate:.1f}% (v1 {v1_rate:.1f}%)", "<= 1%, at most 1 pt above v1",
         v2_rate <= MAX_ERROR_RATE and v2_rate - v1_rate <= MAX_ERROR_RATE_ABOVE_V1),
        ("Latency", "no v2 requests" if latency is None else f"v2 p95 {latency:.0f} ms", "<= 2000 ms",
         latency is not None and latency <= MAX_P95_MS),
        ("Correctness", "no v2 requests" if correct is None else f"{correct:.0f}% correct", ">= 95%",
         correct is not None and correct >= MIN_CORRECT),
        ("Cost", f"{tokens:.0f} tokens per model call, Azure ${spend:.2f}", "<= 1500 tokens, < $8",
         tokens <= MAX_TOKENS_PER_REQUEST and spend < MAX_SPEND),
    ]
    for name, value, threshold, ok in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<13} {value:<40} (rule: {threshold})")
    passed = all(ok for *_, ok in rows)
    print("All criteria met." if passed else "A criterion was violated.")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
