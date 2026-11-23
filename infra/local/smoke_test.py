"""End-to-end smoke test for the local Online Boutique stack.

Runs in a container from the v1 recommendationservice image (see
smoke-test.sh), which already ships grpcio and the generated demo_pb2 stubs.
Works against v1 or v2.

Checks:
  1. The frontend serves the home page and a product page.
  2. ListRecommendations honours its contract: at most 5 product IDs, every ID
     exists in the catalog, and no ID from the request is echoed back.
  3. Recommendation API version 2 (docs/api.md): max_results is honoured
     (0 = 5, capped at 10), and `recommendations` lists the same products as
     `product_ids`, each with a non-empty reason.

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
MAX_RESULTS_CAP = 10
RPC_TIMEOUT_SECONDS = 5
# v2 on a local CPU model needs 20-40 s per new decision. A shorter deadline
# would make v2 fall back (still a valid answer) but leave the abandoned model
# request running in Ollama, slowing every request after it.
RECOMMENDATION_TIMEOUT_SECONDS = 90
PAGE_TIMEOUT_SECONDS = 90


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


def call_recommendations(cart_ids, max_results=0):
    with grpc.insecure_channel(RECOMMENDATION_ADDR) as channel:
        stub = demo_pb2_grpc.RecommendationServiceStub(channel)
        request = demo_pb2.ListRecommendationsRequest(user_id="smoke-test", product_ids=cart_ids,
                                                      max_results=max_results)
        return stub.ListRecommendations(request, timeout=RECOMMENDATION_TIMEOUT_SECONDS)


def list_recommendations(cart_ids):
    return list(call_recommendations(cart_ids).product_ids)


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


def check_api_version_2(catalog_ids, cart_ids, max_results):
    response = call_recommendations(cart_ids, max_results)
    ids = list(response.product_ids)
    expected = min(max_results, MAX_RESULTS_CAP) if max_results > 0 else MAX_RECOMMENDATIONS
    if len(ids) != expected:
        raise AssertionError(f"max_results={max_results}: expected {expected} products, got {len(ids)}")
    if [r.product_id for r in response.recommendations] != ids:
        raise AssertionError("recommendations do not match product_ids")
    if not all(r.reason.strip() for r in response.recommendations):
        raise AssertionError("a product has no reason")
    if set(ids) - catalog_ids or set(ids) & set(cart_ids) or len(set(ids)) != len(ids):
        raise AssertionError(f"invalid, repeated or cart product IDs: {ids}")
    return f"{len(ids)} products, e.g. {response.recommendations[0].reason!r}"


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
    cart = sorted(catalog_ids)[:2]
    for max_results in (4, 15):
        run(f"API version 2, max_results={max_results}",
            lambda m=max_results: check_api_version_2(catalog_ids, cart, m))

    total = 6
    print(f"\n{total - failures}/{total} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
