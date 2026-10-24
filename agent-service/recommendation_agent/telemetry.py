"""Per-request decision records.

Every request produces one record. It is always written to stdout as a JSON
log line (collected by Log Analytics on Azure) and, if Cosmos DB is
configured, stored in the agent-decisions container. The record carries what
the canary needs: version, outcome, latency, tokens and estimated cost.
"""

import json
import logging
import queue
import sys
import threading
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SERVICE_VERSION = "v2"


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with any `record` dict merged in."""

    def format(self, record):
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        entry.update(getattr(record, "record", {}))
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def configure_logging(level=logging.INFO):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)


def estimate_cost(prompt_tokens, completion_tokens, input_price_per_mtok, output_price_per_mtok):
    return (prompt_tokens * input_price_per_mtok + completion_tokens * output_price_per_mtok) / 1_000_000


def build_record(user_id, context_ids, decision, latency_ms, model_name, cost_usd):
    return {
        "id": str(uuid.uuid4()),
        "userId": user_id or "anonymous",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": SERVICE_VERSION,
        "contextProductIds": list(context_ids),
        "recommendedProductIds": list(decision.product_ids),
        "outcome": decision.outcome,
        "fallbackReason": decision.fallback_reason,
        "reason": decision.reason,
        "toolCalls": decision.tool_calls,
        "steps": decision.steps,
        "toppedUp": decision.topped_up,
        "model": model_name,
        "promptTokens": decision.prompt_tokens,
        "completionTokens": decision.completion_tokens,
        "estimatedCostUsd": round(cost_usd, 8),
        "latencyMs": round(latency_ms, 1),
    }


class CosmosSink:
    """Writes records to Cosmos DB on a background thread.

    Writes are best effort: the request path never waits on Cosmos DB, and
    records are dropped (with a warning) if the queue is full or a write fails.
    """

    def __init__(self, endpoint, key, database, container, max_queue=1000):
        from azure.cosmos import CosmosClient  # imported only when Cosmos DB is configured

        client = CosmosClient(endpoint, credential=key)
        self._container = client.get_database_client(database).get_container_client(container)
        self._queue = queue.Queue(maxsize=max_queue)
        threading.Thread(target=self._drain, name="cosmos-sink", daemon=True).start()

    def write(self, record):
        try:
            self._queue.put_nowait(record)
        except queue.Full:
            logger.warning("cosmos queue full; dropping decision record")

    def _drain(self):
        while True:
            record = self._queue.get()
            try:
                self._container.upsert_item(record)
            except Exception as exc:  # never let storage problems affect serving
                logger.warning("cosmos write failed: %s", exc)


class DecisionLog:
    def __init__(self, sink=None):
        self._sink = sink

    def write(self, record):
        logger.info("recommendation served", extra={"record": record})
        if self._sink is not None:
            self._sink.write(record)
