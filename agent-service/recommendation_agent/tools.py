"""Tools the model can call, in OpenAI function-calling format.

Three tools read productcatalogservice; the fourth, `recommend`, is how the
model returns its final answer. Tool results are JSON strings.
"""

import json

RECOMMEND = "recommend"

_LIST_CATALOG = {
    "type": "function",
    "function": {
        "name": "list_catalog",
        "description": "List every product in the store with its id, name and categories.",
        "parameters": {"type": "object", "properties": {}},
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
        "description": "Search product names and descriptions for a keyword, e.g. 'kitchen' or 'summer'.",
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

ALL_TOOLS = [_LIST_CATALOG, _GET_PRODUCTS, _SEARCH_CATALOG, _RECOMMEND]
FINAL_TOOLS = [_RECOMMEND]


class ToolExecutor:
    """Runs the catalog tools against a CatalogClient."""

    def __init__(self, catalog):
        self._catalog = catalog

    def run(self, name, arguments):
        handler = {
            "list_catalog": self._list_catalog,
            "get_products": self._get_products,
            "search_catalog": self._search_catalog,
        }.get(name)
        if handler is None:
            return json.dumps({"error": f"unknown tool {name!r}"})
        try:
            return json.dumps(handler(**arguments))
        except TypeError as exc:  # wrong or missing arguments from the model
            return json.dumps({"error": f"bad arguments for {name}: {exc}"})

    def _list_catalog(self):
        return {"products": [p.summary() for p in self._catalog.all_products().values()]}

    def _get_products(self, product_ids):
        found = [self._catalog.get(pid) for pid in product_ids]
        return {"products": [p.detail() for p in found if p is not None]}

    def _search_catalog(self, query):
        return {"products": [p.summary() for p in self._catalog.search(query)]}
