import itertools

import pytest

from recommendation_agent.catalog import Product
from recommendation_agent.model import ModelTurn, ToolCall

# The real Online Boutique catalog ids, with simplified data.
PRODUCTS = {
    "OLJCESPC7Z": Product("OLJCESPC7Z", "Sunglasses", "Add a modern touch.", ("accessories",)),
    "66VCHSJNUP": Product("66VCHSJNUP", "Tank Top", "Perfectly cropped cotton tank.", ("clothing", "tops")),
    "1YMWWN1N4O": Product("1YMWWN1N4O", "Watch", "Personal timekeeper.", ("accessories",)),
    "L9ECAV7KIM": Product("L9ECAV7KIM", "Loafers", "Fashionable leather loafers.", ("footwear",)),
    "2ZYFJ3GM2N": Product("2ZYFJ3GM2N", "Hairdryer", "Hot air for your hair.", ("hair", "beauty")),
    "0PUK6V6EV0": Product("0PUK6V6EV0", "Candle Holder", "Brings light to any room.", ("decor", "home")),
    "LS4PSXUNUM": Product("LS4PSXUNUM", "Salt & Pepper Shakers", "Season your food.", ("kitchen",)),
    "9SIQT8TOJO": Product("9SIQT8TOJO", "Bamboo Glass Jar", "Store your food.", ("kitchen",)),
    "6E92ZMYYFZ": Product("6E92ZMYYFZ", "Mug", "A simple mug.", ("kitchen",)),
}


class FakeCatalog:
    def __init__(self, products=PRODUCTS):
        self.products = dict(products)
        self.search_queries = []

    def all_products(self):
        return dict(self.products)

    def get(self, product_id):
        return self.products.get(product_id)

    def search(self, query):
        self.search_queries.append(query)
        q = query.lower()
        return [p for p in self.products.values() if q in p.name.lower() or q in p.description.lower()]


class ScriptedModel:
    """Returns pre-written turns in order; records what it was asked."""

    name = "scripted-test-model"

    def __init__(self, *turns, error=None, on_call=None):
        self._turns = list(turns)
        self._error = error
        self._on_call = on_call
        self.calls = []

    def complete(self, messages, tools, timeout):
        self.calls.append({"messages": list(messages), "tools": tools, "timeout": timeout})
        if self._on_call:
            self._on_call()
        if self._error:
            raise self._error
        if not self._turns:
            raise AssertionError("model called more times than scripted")
        return self._turns.pop(0)


_ids = itertools.count(1)


def tool_turn(name, prompt_tokens=100, completion_tokens=20, **arguments):
    return ModelTurn(
        content="",
        tool_calls=[ToolCall(id=f"call_{next(_ids)}", name=name, arguments=arguments)],
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def catalog():
    return FakeCatalog()


@pytest.fixture
def clock():
    return FakeClock()
