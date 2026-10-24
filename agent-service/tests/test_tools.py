import json

from recommendation_agent.tools import ToolExecutor


def run(catalog, name, **arguments):
    return json.loads(ToolExecutor(catalog).run(name, arguments))


def test_browse_category_lists_matching_products(catalog):
    products = run(catalog, "browse_category", category="Kitchen")["products"]
    assert {p["name"] for p in products} == {"Salt & Pepper Shakers", "Bamboo Glass Jar", "Mug"}
    assert "Unknown category" in run(catalog, "browse_category", category="garden")["hint"]


def test_get_products_skips_unknown_ids(catalog):
    products = run(catalog, "get_products", product_ids=["OLJCESPC7Z", "MISSING"])["products"]
    assert [p["id"] for p in products] == ["OLJCESPC7Z"]
    assert "description" in products[0]


def test_search_catalog_uses_catalog_search(catalog):
    products = run(catalog, "search_catalog", query="mug")["products"]
    assert [p["name"] for p in products] == ["Mug"]
    assert catalog.search_queries == ["mug"]


def test_empty_search_returns_a_hint(catalog):
    result = run(catalog, "search_catalog", query="kitchen accessories")
    assert result["products"] == []
    assert "single keyword" in result["hint"]


def test_unknown_tool_and_bad_arguments_return_errors(catalog):
    assert "unknown tool" in run(catalog, "list_catalog")["error"]
    assert "bad arguments" in run(catalog, "get_products", wrong="x")["error"]


def test_loosely_typed_arguments_still_work(catalog):
    assert [p["id"] for p in run(catalog, "get_products", product_ids="OLJCESPC7Z")["products"]] == ["OLJCESPC7Z"]
    assert "Unknown category" in run(catalog, "browse_category", category=None)["hint"]
