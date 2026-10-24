"""The recommendation agent.

The model decides what to recommend. The agent hands it the shopper's
products, the store's categories and a shortlist of related candidates; the
model may browse or search the catalog for more, then calls `recommend`.
The agent enforces the v1
contract on whatever the model returns and falls back to v1's random choice
on any failure, so the client always gets a valid answer.

Outcomes recorded per request:
  agent     the model chose the products (possibly topped up to the limit)
  cached    a recent model decision for the same context was reused
  fallback  the model failed, timed out or returned nothing usable; v1 answered
"""

import json
import logging
import random
import threading
import time
from dataclasses import dataclass, field

from .fallback import random_recommendations
from .tools import ALL_TOOLS, FINAL_TOOLS, RECOMMEND, ToolExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the recommendation engine of an online store.
The user message lists the shopper's products, the store's categories and a shortlist of candidates.
Choose up to {limit} products the shopper is most likely to want next:
complementary items first, then items from related categories.
The shortlist is usually enough: then call `recommend` immediately.
Call browse_category, search_catalog or get_products only if you need more options or detail.
Only recommend ids you have seen in this conversation, never the shopper's own products,
and finish by calling `recommend` exactly once."""

# Candidates included in the prompt; the rest of the catalog is reachable via tools.
DEFAULT_SHORTLIST_SIZE = 20

# Leave this much of the time budget for the fallback path.
_SAFETY_MARGIN_SECONDS = 0.3


class AgentError(Exception):
    """The model did not produce a usable answer."""


@dataclass
class Decision:
    product_ids: list
    outcome: str
    fallback_reason: str = ""
    reason: str = ""
    tool_calls: list = field(default_factory=list)
    steps: int = 0
    topped_up: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


def build_shortlist(products, context_ids, size, rng):
    """Candidates for the prompt: products sharing the most categories with the
    shopper's products first (shuffled within ties, for variety), then a
    category-balanced sample so an empty or unusual context still gets choices."""
    owned_categories = {c for pid in context_ids if pid in products for c in products[pid].categories}
    others = [p for pid, p in products.items() if pid not in context_ids]
    rng.shuffle(others)

    related = [p for p in others if owned_categories & set(p.categories)]
    related.sort(key=lambda p: -len(owned_categories & set(p.categories)))  # stable: keeps the shuffle within ties
    shortlist = related[:size]

    by_category = {}
    for p in others:
        if p not in shortlist:
            by_category.setdefault(p.categories[0] if p.categories else "", []).append(p)
    while len(shortlist) < size and any(by_category.values()):
        for bucket in by_category.values():
            if bucket and len(shortlist) < size:
                shortlist.append(bucket.pop())
    return shortlist


def sanitize(product_ids, catalog_ids, excluded, limit):
    """Keep valid, new, unique catalog ids in the model's order, up to `limit`."""
    result = []
    for pid in product_ids:
        if isinstance(pid, str) and pid in catalog_ids and pid not in excluded and pid not in result:
            result.append(pid)
    return result[:limit]


class _DecisionCache:
    """Small in-memory cache of model decisions, keyed by shopper context."""

    def __init__(self, ttl_seconds, max_entries=256, clock=time.monotonic):
        self._ttl = ttl_seconds
        self._max = max_entries
        self._clock = clock
        self._lock = threading.Lock()
        self._entries = {}

    def get(self, key):
        """Return (product_ids, reason) of a fresh decision, or None."""
        if self._ttl <= 0:
            return None
        with self._lock:
            entry = self._entries.get(key)
            if entry and self._clock() - entry[0] < self._ttl:
                return list(entry[1]), entry[2]
            self._entries.pop(key, None)
            return None

    def put(self, key, product_ids, reason):
        if self._ttl <= 0:
            return
        with self._lock:
            if len(self._entries) >= self._max:
                self._entries.pop(next(iter(self._entries)))
            self._entries[key] = (self._clock(), list(product_ids), reason)


class RecommendationAgent:
    def __init__(self, catalog, model, max_recommendations=5, max_steps=4, timeout_seconds=8.0,
                 cache_ttl_seconds=600, shortlist_size=DEFAULT_SHORTLIST_SIZE, clock=time.monotonic, rng=random):
        self._catalog = catalog
        self._model = model
        self._tools = ToolExecutor(catalog)
        self._limit = max_recommendations
        self._shortlist_size = shortlist_size
        self._max_steps = max_steps
        self._timeout = timeout_seconds
        self._cache = _DecisionCache(cache_ttl_seconds, clock=clock)
        self._clock = clock
        self._rng = rng

    @property
    def model_name(self):
        return getattr(self._model, "name", "none")

    def recommend(self, context_ids, time_budget=None):
        """Return a Decision for the shopper's products.

        time_budget caps the work at the caller's gRPC deadline, if it has one.
        Raises only if the catalog itself is unreachable (v1 fails then too).
        """
        catalog_ids = set(self._catalog.all_products())
        excluded = set(context_ids)
        budget = self._timeout if time_budget is None else min(self._timeout, time_budget)
        deadline = self._clock() + budget - _SAFETY_MARGIN_SECONDS
        cache_key = tuple(sorted(excluded))

        cached = self._cache.get(cache_key)
        if cached is not None:
            cached_ids, cached_reason = cached
            chosen = sanitize(cached_ids, catalog_ids, excluded, self._limit)
            if chosen:
                decision = Decision(product_ids=chosen, outcome="cached", reason=cached_reason)
                return self._top_up(decision, catalog_ids, excluded)

        decision = Decision(product_ids=[], outcome="agent")
        try:
            if self._model is None:
                raise AgentError("no model configured")
            self._run(context_ids, catalog_ids, excluded, deadline, decision)
        except Exception as exc:  # any model, network or parsing failure
            logger.warning("agent fallback: %s", exc)
            decision.outcome = "fallback"
            decision.fallback_reason = f"{type(exc).__name__}: {exc}"[:300]
            decision.product_ids = random_recommendations(catalog_ids, excluded, self._limit, self._rng)
            return decision

        self._cache.put(cache_key, decision.product_ids, decision.reason)
        return self._top_up(decision, catalog_ids, excluded)

    def _run(self, context_ids, catalog_ids, excluded, deadline, decision):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(limit=self._limit)},
            {"role": "user", "content": self._describe_context(context_ids)},
        ]
        for step in range(1, self._max_steps + 1):
            remaining = deadline - self._clock()
            if remaining <= 0:
                raise AgentError("time budget exhausted")
            # On the last step only `recommend` is offered, forcing an answer.
            tools = FINAL_TOOLS if step == self._max_steps else ALL_TOOLS
            turn = self._model.complete(messages, tools, timeout=remaining)
            decision.steps = step
            decision.prompt_tokens += turn.prompt_tokens
            decision.completion_tokens += turn.completion_tokens
            if self._clock() > deadline:
                raise AgentError("time budget exhausted")

            if not turn.tool_calls:
                # Some models answer in text instead of calling the tool.
                mentioned = [pid for pid in catalog_ids if pid in turn.content]
                return self._accept(mentioned, "", catalog_ids, excluded, decision)

            messages.append(turn.as_message())
            for call in turn.tool_calls:
                decision.tool_calls.append({"name": call.name, "arguments": call.arguments})
                if call.name == RECOMMEND:
                    return self._accept(call.arguments.get("product_ids", []),
                                        call.arguments.get("reason", ""), catalog_ids, excluded, decision)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": self._tools.run(call.name, call.arguments),
                })
        raise AgentError(f"no recommendation after {self._max_steps} steps")

    def _accept(self, proposed, reason, catalog_ids, excluded, decision):
        chosen = sanitize(proposed, catalog_ids, excluded, self._limit)
        if not chosen:
            raise AgentError(f"model proposed no valid products: {json.dumps(proposed)[:200]}")
        decision.product_ids = chosen
        decision.reason = str(reason)[:300]

    def _describe_context(self, context_ids):
        """Pre-fetch what most decisions need, so the model can usually answer in
        one call: the shopper's products in detail, the store's categories and a
        shortlist of related candidates. Prompt size stays bounded however large
        the catalog is."""
        products = self._catalog.all_products()
        owned = [products[pid] for pid in context_ids if pid in products]
        counts = {}
        for p in products.values():
            for c in p.categories:
                counts[c] = counts.get(c, 0) + 1
        categories = ", ".join(f"{c} ({n})" for c, n in sorted(counts.items()))
        shortlist = build_shortlist(products, context_ids, self._shortlist_size, self._rng)

        # Plain "id: name (categories)" lines use about half the tokens of JSON,
        # which matters for prompt-processing time and per-token cost.
        def line(p, with_description=False):
            text = f"- {p.id}: {p.name} ({', '.join(p.categories)})"
            return f"{text}. {p.description}" if with_description else text

        if owned:
            shopper = "Shopper's products (do not recommend these):\n" + "\n".join(line(p, True) for p in owned)
        else:
            shopper = "The shopper has no products yet; recommend a varied selection."
        return (f"{shopper}\n"
                f"Store categories: {categories}\n"
                "Shortlist:\n" + "\n".join(line(p) for p in shortlist))

    def _top_up(self, decision, catalog_ids, excluded):
        """Fill to the limit with random products so the response size matches v1."""
        missing = self._limit - len(decision.product_ids)
        if missing > 0:
            extra = random_recommendations(catalog_ids, excluded | set(decision.product_ids), missing, self._rng)
            decision.product_ids += extra
            decision.topped_up = len(extra)
        return decision
