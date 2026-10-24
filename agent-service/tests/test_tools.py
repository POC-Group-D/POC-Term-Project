import json

from recommendation_agent.tools import ToolExecutor


def run(catalog, name, **arguments):
    return json.loads(ToolExecutor(catalog).run(name, arguments))


def test_list_catalog_returns_compact_summaries(catalog):
    products = run(catalog, "list_catalog")["products"]
    assert len(products) == 9
    assert set(products[0]) == {"id", "name", "categories"}


def test_get_products_skips_unknown_ids(catalog):
    products = run(catalog, "get_products", product_ids=["OLJCESPC7Z", "MISSING"])["products"]
    assert [p["id"] for p in products] == ["OLJCESPC7Z"]
    assert "description" in products[0]


def test_search_catalog_uses_catalog_search(catalog):
    products = run(catalog, "search_catalog", query="mug")["products"]
    assert [p["name"] for p in products] == ["Mug"]
    assert catalog.search_queries == ["mug"]


def test_unknown_tool_and_bad_arguments_return_errors(catalog):
    assert "unknown tool" in run(catalog, "delete_everything")["error"]
    assert "bad arguments" in run(catalog, "get_products", wrong="x")["error"]
