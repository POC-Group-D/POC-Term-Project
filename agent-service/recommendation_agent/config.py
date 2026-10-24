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

    # Model (Hugging Face Inference Providers, OpenAI-compatible API).
    hf_token: str
    hf_base_url: str
    hf_model: str
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
            hf_token=os.environ.get("HF_TOKEN", ""),
            hf_base_url=os.environ.get("HF_BASE_URL", "https://router.huggingface.co/v1"),
            hf_model=os.environ.get("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
            model_max_tokens=_int("MODEL_MAX_TOKENS", 300),
            input_price_per_mtok=_float("MODEL_INPUT_PRICE_PER_MTOK", 0.0),
            output_price_per_mtok=_float("MODEL_OUTPUT_PRICE_PER_MTOK", 0.0),
            max_recommendations=_int("MAX_RECOMMENDATIONS", 5),
            max_agent_steps=_int("MAX_AGENT_STEPS", 4),
            agent_timeout_seconds=_float("AGENT_TIMEOUT_SECONDS", 8.0),
            cache_ttl_seconds=_int("CACHE_TTL_SECONDS", 600),
            cosmos_endpoint=os.environ.get("COSMOS_ENDPOINT", ""),
            cosmos_key=os.environ.get("COSMOS_KEY", ""),
            cosmos_database=os.environ.get("COSMOS_DATABASE", "recommendations"),
            cosmos_container=os.environ.get("COSMOS_CONTAINER", "agent-decisions"),
        )
