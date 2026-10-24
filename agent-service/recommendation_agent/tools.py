"""Tools the model can call, in OpenAI function-calling format.

Three tools read productcatalogservice; the fourth, `recommend`, is how the
model returns its final answer. Tool results are JSON strings. The agent's
prompt already carries a shortlist, so these tools are for when the model
wants more options or more detail.
"""

import json

RECOMMEND = "recommend"
MAX_CATEGORY_RESULTS = 40

_BROWSE_CATEGORY = {
    "type": "function",
    "function": {
        "name": "browse_category",
        "description": "List the products in one store category, e.g. 'kitchen' or 'footwear'.",
        "parameters": {
            "type": "object",
            "properties": {"category": {"type": "string"}},
            "required": ["category"],
        },
    },
}

_GET_PRODUCTS = {
    "type": "function",
    "function": {
        "name": "get_products",
        "description": "Get the name, categories and description of specific products.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["product_ids"],
        },
    },
}

_SEARCH_CATALOG = {
    "type": "function",
    "function": {
        "name": "search_catalog",
        "description": "Search product names and descriptions for ONE keyword, e.g. 'kitchen' or 'summer'.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}

_RECOMMEND = {
    "type": "function",
    "function": {
        "name": RECOMMEND,
        "description": "Return the final recommendations, best match first. Call exactly once, last.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Catalog product ids, never ones the shopper already has.",
                },
                "reason": {"type": "string", "description": "One short sentence explaining the choice."},
            },
            "required": ["product_ids"],
        },
    },
}

ALL_TOOLS = [_BROWSE_CATEGORY, _GET_PRODUCTS, _SEARCH_CATALOG, _RECOMMEND]
FINAL_TOOLS = [_RECOMMEND]


class ToolExecutor:
    """Runs the catalog tools against a CatalogClient."""

    def __init__(self, catalog):
        self._catalog = catalog

    def run(self, name, arguments):
        handler = {
            "browse_category": self._browse_category,
            "get_products": self._get_products,
            "search_catalog": self._search_catalog,
        }.get(name)
        if handler is None:
            return json.dumps({"error": f"unknown tool {name!r}"})
        try:
            return json.dumps(handler(**arguments))
        except (TypeError, AttributeError, ValueError) as exc:  # malformed arguments from the model
            return json.dumps({"error": f"bad arguments for {name}: {exc}"})

    def _browse_category(self, category):
        wanted = str(category).lower().strip()
        matches = [p.summary() for p in self._catalog.all_products().values()
                   if wanted in (c.lower() for c in p.categories)]
        if not matches:
            return {"products": [], "hint": "Unknown category. Use one from the store category list."}
        return {"products": matches[:MAX_CATEGORY_RESULTS]}

    def _get_products(self, product_ids):
        if isinstance(product_ids, str):  # a single id instead of a list
            product_ids = [product_ids]
        found = [self._catalog.get(pid) for pid in product_ids]
        return {"products": [p.detail() for p in found if p is not None]}

    def _search_catalog(self, query):
        results = [p.summary() for p in self._catalog.search(str(query))]
        if not results:
            return {"products": [], "hint": "No match. Try a single keyword, or browse a category."}
        return {"products": results}
