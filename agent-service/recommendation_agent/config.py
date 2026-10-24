"""Service configuration, read once from environment variables."""

import os
from dataclasses import dataclass


def _float(name, default):
    return float(os.environ.get(name, default))


def _int(name, default):
    return int(os.environ.get(name, default))


@dataclass(frozen=True)
class Settings:
    port: int
    catalog_addr: str

    # Model: any OpenAI-compatible chat API with tool calling, e.g. a local
    # Ollama server, Hugging Face Inference Providers or GitHub Models.
    model_base_url: str
    model_api_key: str
    model_name: str
    model_max_tokens: int
    # USD per million tokens, used to estimate cost per request.
    input_price_per_mtok: float
    output_price_per_mtok: float

    # Agent behaviour.
    max_recommendations: int
    max_agent_steps: int
    agent_timeout_seconds: float
    # Reuse a model decision for the same context for this long (0 disables).
    cache_ttl_seconds: int
    # Related candidates put in the prompt; the rest are reachable via tools.
    shortlist_size: int

    # Optional Cosmos DB sink for per-request decision records.
    cosmos_endpoint: str
    cosmos_key: str
    cosmos_database: str
    cosmos_container: str

    @classmethod
    def from_env(cls):
        catalog_addr = os.environ.get("PRODUCT_CATALOG_SERVICE_ADDR", "")
        if not catalog_addr:
            raise RuntimeError("PRODUCT_CATALOG_SERVICE_ADDR environment variable not set")
        return cls(
            port=_int("PORT", 8080),
            catalog_addr=catalog_addr,
            model_base_url=os.environ.get("MODEL_BASE_URL", ""),
            model_api_key=os.environ.get("MODEL_API_KEY", ""),
            model_name=os.environ.get("MODEL_NAME", "qwen3:4b-instruct"),
            model_max_tokens=_int("MODEL_MAX_TOKENS", 300),
            input_price_per_mtok=_float("MODEL_INPUT_PRICE_PER_MTOK", 0.0),
            output_price_per_mtok=_float("MODEL_OUTPUT_PRICE_PER_MTOK", 0.0),
            max_recommendations=_int("MAX_RECOMMENDATIONS", 5),
            max_agent_steps=_int("MAX_AGENT_STEPS", 4),
            agent_timeout_seconds=_float("AGENT_TIMEOUT_SECONDS", 8.0),
            cache_ttl_seconds=_int("CACHE_TTL_SECONDS", 600),
            shortlist_size=_int("SHORTLIST_SIZE", 20),
            cosmos_endpoint=os.environ.get("COSMOS_ENDPOINT", ""),
            cosmos_key=os.environ.get("COSMOS_KEY", ""),
            cosmos_database=os.environ.get("COSMOS_DATABASE", "recommendations"),
            cosmos_container=os.environ.get("COSMOS_CONTAINER", "agent-decisions"),
        )
