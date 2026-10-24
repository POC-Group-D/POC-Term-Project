"""End-to-end over real gRPC: a fake productcatalogservice plus the v2 server,
called with the same stub the frontend uses."""

import random
from concurrent import futures

import grpc
import pytest

from recommendation_agent.agent import RecommendationAgent
from recommendation_agent.catalog import CatalogClient
from recommendation_agent.config import Settings
from recommendation_agent.proto import demo_pb2, demo_pb2_grpc
from recommendation_agent.server import RecommendationService
from recommendation_agent.telemetry import DecisionLog

from .conftest import PRODUCTS, ScriptedModel, tool_turn


class CatalogServicer(demo_pb2_grpc.ProductCatalogServiceServicer):
    def ListProducts(self, request, context):
        return demo_pb2.ListProductsResponse(products=[
            demo_pb2.Product(id=p.id, name=p.name, description=p.description, categories=p.categories)
            for p in PRODUCTS.values()
        ])

    def SearchProducts(self, request, context):
        q = request.query.lower()
        return demo_pb2.SearchProductsResponse(results=[
            demo_pb2.Product(id=p.id, name=p.name) for p in PRODUCTS.values() if q in p.name.lower()
        ])


class RecordingLog(DecisionLog):
    def __init__(self):
        super().__init__()
        self.records = []

    def write(self, record):
        self.records.append(record)


def start_server(add_servicer):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    add_servicer(server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    return server, f"127.0.0.1:{port}"


@pytest.fixture
def stack(monkeypatch):
    catalog_server, catalog_addr = start_server(
        lambda s: demo_pb2_grpc.add_ProductCatalogServiceServicer_to_server(CatalogServicer(), s))
    monkeypatch.setenv("PRODUCT_CATALOG_SERVICE_ADDR", catalog_addr)
    monkeypatch.setenv("MODEL_INPUT_PRICE_PER_MTOK", "0.5")
    monkeypatch.setenv("MODEL_OUTPUT_PRICE_PER_MTOK", "1.0")
    settings = Settings.from_env()

    model = ScriptedModel(
        tool_turn("search_catalog", query="mug"),
        tool_turn("recommend", product_ids=["6E92ZMYYFZ", "9SIQT8TOJO"], reason="Kitchen set."),
    )
    agent = RecommendationAgent(CatalogClient(catalog_addr), model, cache_ttl_seconds=0, rng=random.Random(1))
    log = RecordingLog()
    rec_server, rec_addr = start_server(
        lambda s: demo_pb2_grpc.add_RecommendationServiceServicer_to_server(
            RecommendationService(agent, log, settings), s))

    channel = grpc.insecure_channel(rec_addr)
    yield demo_pb2_grpc.RecommendationServiceStub(channel), log
    channel.close()
    rec_server.stop(None)
    catalog_server.stop(None)


def test_same_api_as_v1_and_one_record_per_request(stack):
    stub, log = stack
    request = demo_pb2.ListRecommendationsRequest(user_id="session-1", product_ids=["LS4PSXUNUM"])

    response = stub.ListRecommendations(request, timeout=5)

    ids = list(response.product_ids)
    assert ids[:2] == ["6E92ZMYYFZ", "9SIQT8TOJO"]
    assert len(ids) == 5 and "LS4PSXUNUM" not in ids and set(ids) <= set(PRODUCTS)

    [record] = log.records
    assert record["version"] == "v2"
    assert record["userId"] == "session-1"
    assert record["outcome"] == "agent"
    assert record["recommendedProductIds"] == ids
    assert record["promptTokens"] == 200 and record["completionTokens"] == 40
    assert record["estimatedCostUsd"] == pytest.approx((200 * 0.5 + 40 * 1.0) / 1_000_000)
    assert record["latencyMs"] > 0
