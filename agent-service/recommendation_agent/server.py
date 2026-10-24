"""gRPC entry point: recommendationservice v2 with the same API as v1."""

import logging
import time
from concurrent import futures

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from .agent import RecommendationAgent
from .catalog import CatalogClient
from .config import Settings
from .model import ChatModel
from .proto import demo_pb2, demo_pb2_grpc
from .telemetry import CosmosSink, DecisionLog, build_record, configure_logging, estimate_cost

logger = logging.getLogger(__name__)


class RecommendationService(demo_pb2_grpc.RecommendationServiceServicer):
    def __init__(self, agent, decision_log, settings):
        self._agent = agent
        self._log = decision_log
        self._settings = settings

    def ListRecommendations(self, request, context):
        started = time.perf_counter()
        context_ids = list(request.product_ids)
        try:
            decision = self._agent.recommend(context_ids, time_budget=context.time_remaining())
        except grpc.RpcError as exc:
            # The catalog is down; v1 fails the same way in this case.
            logger.error("catalog unavailable: %s", exc)
            context.abort(grpc.StatusCode.UNAVAILABLE, "product catalog unavailable")

        latency_ms = (time.perf_counter() - started) * 1000
        cost = estimate_cost(decision.prompt_tokens, decision.completion_tokens,
                             self._settings.input_price_per_mtok, self._settings.output_price_per_mtok)
        self._log.write(build_record(request.user_id, context_ids, decision, latency_ms,
                                     self._agent.model_name, cost))
        return demo_pb2.ListRecommendationsResponse(product_ids=decision.product_ids)


def build_model(settings):
    if not settings.model_base_url:
        logger.warning("MODEL_BASE_URL not set: every request will use the v1 fallback")
        return None
    return ChatModel(settings.model_base_url, settings.model_api_key,
                     settings.model_name, settings.model_max_tokens)


def build_sink(settings):
    if not (settings.cosmos_endpoint and settings.cosmos_key):
        logger.info("Cosmos DB not configured: decision records go to logs only")
        return None
    return CosmosSink(settings.cosmos_endpoint, settings.cosmos_key,
                      settings.cosmos_database, settings.cosmos_container)


def serve():
    configure_logging()
    settings = Settings.from_env()
    agent = RecommendationAgent(
        catalog=CatalogClient(settings.catalog_addr),
        model=build_model(settings),
        max_recommendations=settings.max_recommendations,
        max_steps=settings.max_agent_steps,
        timeout_seconds=settings.agent_timeout_seconds,
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    demo_pb2_grpc.add_RecommendationServiceServicer_to_server(
        RecommendationService(agent, DecisionLog(build_sink(settings)), settings), server)
    health_servicer = health.HealthServicer()
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    server.add_insecure_port(f"[::]:{settings.port}")
    server.start()
    logger.info("recommendationservice v2 listening on port %s (model: %s)", settings.port, agent.model_name)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
