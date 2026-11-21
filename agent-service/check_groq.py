"""Exercise the v2 recommendation agent against Groq using the checked-in catalog."""

import argparse
import json
import logging
import math
import os
import random
import shlex
import time
from collections import Counter
from pathlib import Path

from recommendation_agent.agent import RecommendationAgent
from recommendation_agent.catalog import Product
from recommendation_agent.model import ChatModel
from recommendation_agent.tools import RECOMMEND

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "infra/local/.env"
CATALOG_FILE = ROOT / "catalog/productcatalogservice/products.json"
MODEL = "openai/gpt-oss-20b"
GROQ_URL = "https://api.groq.com/openai/v1"
LATENCY_TARGET_MS = 2000
RECOMMENDATION_LIMIT = 5
CASES = (
    ("empty cart", ()),
    ("Mug", ("Mug",)),
    ("French Press", ("French Press",)),
    ("Yoga Mat", ("Yoga Mat",)),
    ("Rain Jacket and Hiking Boots", ("Rain Jacket", "Hiking Boots")),
)


def groq_key():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key or not ENV_FILE.is_file():
        return key
    for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        name, _, value = line.partition("=")
        if name.strip().removeprefix("export ").strip() == "GROQ_API_KEY":
            parts = shlex.split(value, comments=True)
            return parts[0] if len(parts) == 1 else ""
    return ""


class LocalCatalog:
    """Read the same catalog data used by the shop without starting Docker."""

    def __init__(self):
        rows = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))["products"]
        self.products = {
            row["id"]: Product(row["id"], row["name"], row["description"], tuple(row["categories"]))
            for row in rows
        }

    def all_products(self):
        return self.products


def run_check(key, rounds):
    catalog = LocalCatalog()
    ids_by_name = {product.name: pid for pid, product in catalog.products.items()}
    cases = [(label, [ids_by_name[name] for name in names]) for label, names in CASES]
    model = ChatModel(
        GROQ_URL, key, MODEL, max_tokens=600, reasoning_effort="low",
        tool_choice={"type": "function", "function": {"name": RECOMMEND}},
    )
    agent = RecommendationAgent(
        catalog, model,
        max_recommendations=RECOMMENDATION_LIMIT, max_steps=1, cache_ttl_seconds=0,
        shortlist_size=12, rng=random.Random(0),
    )
    outcomes = Counter()
    latencies = []
    valid_count = prompt_tokens = completion_tokens = model_picks = 0
    print(f"Groq {MODEL} | {len(cases) * rounds} requests | decision cache disabled")
    for round_number in range(1, rounds + 1):
        for label, context_ids in cases:
            started = time.perf_counter()
            decision = agent.recommend(context_ids)
            elapsed_ms = (time.perf_counter() - started) * 1000
            latencies.append(elapsed_ms)

            ids = decision.product_ids
            unique_ids = set(ids)
            valid = (0 < len(ids) <= RECOMMENDATION_LIMIT and len(ids) == len(unique_ids)
                     and unique_ids <= catalog.products.keys() and unique_ids.isdisjoint(context_ids))
            valid_count += valid
            outcomes[decision.outcome] += 1
            prompt_tokens += decision.prompt_tokens
            completion_tokens += decision.completion_tokens
            picks = len(ids) - decision.topped_up if decision.outcome == "agent" else 0
            model_picks += picks
            names = ", ".join(catalog.products[pid].name if pid in catalog.products else pid for pid in ids)
            detail = decision.fallback_reason.partition(":")[0] if decision.outcome == "fallback" else names
            print(f"{round_number}. {label} | {decision.outcome} | "
                  f"{'valid' if valid else 'invalid'} | {elapsed_ms:.0f} ms | "
                  f"{picks}/{len(ids)} model picks | {detail}")

    count = len(latencies)
    p95 = sorted(latencies)[math.ceil(0.95 * count) - 1]
    print(f"Valid responses {valid_count}/{count} | model decisions {outcomes['agent']}/{count} | "
          f"fallbacks {outcomes['fallback']} | model picks {model_picks}")
    print(f"Local agent p95 {p95:.0f} ms (target {LATENCY_TARGET_MS} ms) | "
          f"reported tokens {prompt_tokens} input + {completion_tokens} output")
    return 0 if valid_count == outcomes["agent"] == count and p95 <= LATENCY_TARGET_MS else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=1, help="repeat the five-case check (default: 1)")
    args = parser.parse_args(argv)
    if args.rounds < 1:
        parser.error("--rounds must be at least 1")
    try:
        key = groq_key()
    except (OSError, ValueError):
        parser.error("Could not read GROQ_API_KEY from infra/local/.env")
    if not key:
        parser.error("Set GROQ_API_KEY from a Groq Free account in infra/local/.env or your environment.")
    # Print the fallback exception type instead of logging provider response bodies.
    logging.getLogger("recommendation_agent.agent").setLevel(logging.ERROR)
    return run_check(key, args.rounds)


if __name__ == "__main__":
    raise SystemExit(main())
