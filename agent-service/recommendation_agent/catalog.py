"""Thin client for productcatalogservice, the agent's source of truth."""

import threading
import time
from dataclasses import dataclass

import grpc

from .proto import demo_pb2, demo_pb2_grpc


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    description: str
    categories: tuple

    def summary(self):
        """Compact view returned by the catalog tools."""
        return {"id": self.id, "name": self.name, "categories": list(self.categories)}

    def detail(self):
        return {**self.summary(), "description": self.description}


def _from_proto(product):
    return Product(
        id=product.id,
        name=product.name,
        description=product.description,
        categories=tuple(product.categories),
    )


class CatalogClient:
    """Reads the product catalog over gRPC, caching the full list briefly.

    The catalog is small and changes rarely, so one ListProducts call serves
    many requests and product lookups are answered from that cache. Free-text
    search goes to the service's SearchProducts RPC.
    """

    def __init__(self, address, cache_seconds=60.0, rpc_timeout=2.0):
        self._stub = demo_pb2_grpc.ProductCatalogServiceStub(grpc.insecure_channel(address))
        self._cache_seconds = cache_seconds
        self._rpc_timeout = rpc_timeout
        self._lock = threading.Lock()
        self._products = {}
        self._fetched_at = 0.0

    def all_products(self):
        with self._lock:
            if not self._products or time.monotonic() - self._fetched_at > self._cache_seconds:
                response = self._stub.ListProducts(demo_pb2.Empty(), timeout=self._rpc_timeout)
                self._products = {p.id: _from_proto(p) for p in response.products}
                self._fetched_at = time.monotonic()
            return dict(self._products)

    def get(self, product_id):
        return self.all_products().get(product_id)

    def search(self, query):
        request = demo_pb2.SearchProductsRequest(query=query)
        response = self._stub.SearchProducts(request, timeout=self._rpc_timeout)
        return [_from_proto(p) for p in response.results]
