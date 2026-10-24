"""End-to-end smoke test for the local Online Boutique stack.

Runs inside the recommendationservice container (see smoke-test.sh), which
already ships grpcio and the generated demo_pb2 stubs.

Checks:
  1. The frontend serves the home page and a product page.
  2. ListRecommendations honours its contract: at most 5 product IDs, every ID
     exists in the catalog, and no ID from the request is echoed back.

These rules are the baseline correctness criteria v2 (the AI agent) must meet.
"""

import os
import sys
import urllib.request

import grpc

import demo_pb2
import demo_pb2_grpc

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://frontend:8080")
RECOMMENDATION_ADDR = os.environ.get("RECOMMENDATION_ADDR", "recommendationservice:8080")
CATALOG_ADDR = os.environ.get("CATALOG_ADDR", "productcatalogservice:3550")
MAX_RECOMMENDATIONS = 5
RPC_TIMEOUT_SECONDS = 5
# Product pages wait for recommendations; v2 on a local CPU model takes ~20 s.
PAGE_TIMEOUT_SECONDS = 60


def check_http(path):
    url = FRONTEND_URL + path
    with urllib.request.urlopen(url, timeout=PAGE_TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise AssertionError(f"GET {url} returned {response.status}")


def list_catalog_ids():
    with grpc.insecure_channel(CATALOG_ADDR) as channel:
        stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)
        response = stub.ListProducts(demo_pb2.Empty(), timeout=RPC_TIMEOUT_SECONDS)
    return {product.id for product in response.products}


def list_recommendations(cart_ids):
    with grpc.insecure_channel(RECOMMENDATION_ADDR) as channel:
        stub = demo_pb2_grpc.RecommendationServiceStub(channel)
        request = demo_pb2.ListRecommendationsRequest(user_id="smoke-test", product_ids=cart_ids)
        response = stub.ListRecommendations(request, timeout=RPC_TIMEOUT_SECONDS)
    return list(response.product_ids)


def check_recommendation_contract(catalog_ids, cart_ids):
    recommended = list_recommendations(cart_ids)
    if not recommended:
        raise AssertionError("no recommendations returned")
    if len(recommended) > MAX_RECOMMENDATIONS:
        raise AssertionError(f"{len(recommended)} recommendations exceeds limit {MAX_RECOMMENDATIONS}")
    unknown = set(recommended) - catalog_ids
    if unknown:
        raise AssertionError(f"unknown product IDs returned: {sorted(unknown)}")
    echoed = set(recommended) & set(cart_ids)
    if echoed:
        raise AssertionError(f"cart items echoed back: {sorted(echoed)}")
    return recommended


def main():
    failures = 0

    def run(name, check):
        nonlocal failures
        try:
            detail = check()
            print(f"PASS  {name}" + (f"  {detail}" if detail else ""))
        except Exception as exc:  # report every failing check, not just the first
            failures += 1
            print(f"FAIL  {name}  {exc}")

    catalog_ids = list_catalog_ids()
    sample_id = sorted(catalog_ids)[0]

    run("frontend home page", lambda: check_http("/"))
    run("frontend product page", lambda: check_http(f"/product/{sample_id}"))
    run("recommendations, empty cart", lambda: check_recommendation_contract(catalog_ids, []))
    run("recommendations, two-item cart",
        lambda: check_recommendation_contract(catalog_ids, sorted(catalog_ids)[:2]))

    print(f"\n{4 - failures}/4 checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
