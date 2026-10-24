import random

import pytest

from recommendation_agent.agent import RecommendationAgent, build_shortlist, sanitize
from recommendation_agent.model import ModelTurn
from recommendation_agent.tools import FINAL_TOOLS

from .conftest import PRODUCTS, ScriptedModel, tool_turn

LIMIT = 5


def make_agent(catalog, model, clock, **overrides):
    options = dict(max_recommendations=LIMIT, max_steps=4, timeout_seconds=8.0,
                   cache_ttl_seconds=0, clock=clock, rng=random.Random(7))
    options.update(overrides)
    return RecommendationAgent(catalog, model, **options)


def assert_v1_contract(decision, context_ids):
    """The rules every response must satisfy, whichever path produced it."""
    ids = decision.product_ids
    assert 0 < len(ids) <= LIMIT
    assert len(set(ids)) == len(ids)
    assert set(ids) <= set(PRODUCTS)
    assert not set(ids) & set(context_ids)


def test_model_choice_is_returned_first_and_topped_up(catalog, clock):
    model = ScriptedModel(
        tool_turn("get_products", product_ids=["LS4PSXUNUM"]),
        tool_turn("recommend", product_ids=["9SIQT8TOJO", "6E92ZMYYFZ"], reason="More kitchen items."),
    )
    decision = make_agent(catalog, model, clock).recommend(["LS4PSXUNUM"])

    assert decision.outcome == "agent"
    assert decision.product_ids[:2] == ["9SIQT8TOJO", "6E92ZMYYFZ"]
    assert decision.topped_up == 3
    assert decision.reason == "More kitchen items."
    assert [c["name"] for c in decision.tool_calls] == ["get_products", "recommend"]
    assert (decision.prompt_tokens, decision.completion_tokens) == (200, 40)
    assert_v1_contract(decision, ["LS4PSXUNUM"])


def test_prompt_has_owned_products_categories_and_shortlist(catalog, clock):
    model = ScriptedModel(tool_turn("recommend", product_ids=["6E92ZMYYFZ"]))
    decision = make_agent(catalog, model, clock).recommend(["LS4PSXUNUM"])

    prompt = model.calls[0]["messages"][1]["content"]
    owned, rest = prompt.split("\nStore categories: ")
    categories, shortlist = rest.split("\nShortlist:\n")
    assert "- LS4PSXUNUM: Salt & Pepper Shakers (kitchen). Season your food." in owned
    assert "kitchen (3)" in categories
    assert "LS4PSXUNUM" not in shortlist
    assert "- 6E92ZMYYFZ: Mug (kitchen)" in shortlist.splitlines()
    # One model call is enough when the model answers directly.
    assert decision.steps == 1


def test_shortlist_puts_related_products_first_and_stays_bounded():
    products = dict(PRODUCTS)
    shortlist = build_shortlist(products, ["LS4PSXUNUM"], size=4, rng=random.Random(3))

    assert len(shortlist) == 4
    assert {p.id for p in shortlist[:2]} == {"9SIQT8TOJO", "6E92ZMYYFZ"}  # the other kitchen items
    assert "LS4PSXUNUM" not in {p.id for p in shortlist}


def test_shortlist_without_context_samples_across_categories():
    shortlist = build_shortlist(dict(PRODUCTS), [], size=5, rng=random.Random(3))

    assert len(shortlist) == 5
    assert len({p.categories[0] for p in shortlist}) == 5


def test_tool_results_are_sent_back_to_the_model(catalog, clock):
    model = ScriptedModel(
        tool_turn("search_catalog", query="kitchen"),
        tool_turn("recommend", product_ids=["6E92ZMYYFZ"]),
    )
    make_agent(catalog, model, clock).recommend(["OLJCESPC7Z"])

    second_call_messages = model.calls[1]["messages"]
    assert second_call_messages[-2]["role"] == "assistant"
    assert second_call_messages[-1]["role"] == "tool"
    assert catalog.search_queries == ["kitchen"]


def test_invalid_duplicate_and_owned_ids_are_removed(catalog, clock):
    model = ScriptedModel(tool_turn(
        "recommend", product_ids=["NOT-A-PRODUCT", "OLJCESPC7Z", "1YMWWN1N4O", "1YMWWN1N4O", 42]))
    decision = make_agent(catalog, model, clock).recommend(["OLJCESPC7Z"])

    assert decision.outcome == "agent"
    assert decision.product_ids[0] == "1YMWWN1N4O"
    assert_v1_contract(decision, ["OLJCESPC7Z"])


def test_no_valid_ids_falls_back_to_v1(catalog, clock):
    model = ScriptedModel(tool_turn("recommend", product_ids=["FAKE1", "FAKE2"]))
    decision = make_agent(catalog, model, clock).recommend(["OLJCESPC7Z"])

    assert decision.outcome == "fallback"
    assert "no valid products" in decision.fallback_reason
    assert len(decision.product_ids) == LIMIT
    assert_v1_contract(decision, ["OLJCESPC7Z"])


def test_model_error_falls_back_to_v1(catalog, clock):
    model = ScriptedModel(error=ConnectionError("provider unreachable"))
    decision = make_agent(catalog, model, clock).recommend(["66VCHSJNUP"])

    assert decision.outcome == "fallback"
    assert "provider unreachable" in decision.fallback_reason
    assert_v1_contract(decision, ["66VCHSJNUP"])


def test_slow_model_hits_the_time_budget(catalog, clock):
    model = ScriptedModel(
        tool_turn("search_catalog", query="kitchen"),
        tool_turn("recommend", product_ids=["6E92ZMYYFZ"]),
        on_call=lambda: clock.advance(5),
    )
    decision = make_agent(catalog, model, clock, timeout_seconds=8.0).recommend([])

    assert decision.outcome == "fallback"
    assert "time budget" in decision.fallback_reason
    assert_v1_contract(decision, [])


def test_caller_deadline_shortens_the_budget(catalog, clock):
    model = ScriptedModel(tool_turn("recommend", product_ids=["6E92ZMYYFZ"]))
    make_agent(catalog, model, clock, timeout_seconds=8.0).recommend([], time_budget=2.0)

    assert model.calls[0]["timeout"] == pytest.approx(1.7)


def test_last_step_only_offers_recommend(catalog, clock):
    model = ScriptedModel(
        tool_turn("search_catalog", query="kitchen"),
        tool_turn("recommend", product_ids=["L9ECAV7KIM"]),
    )
    decision = make_agent(catalog, model, clock, max_steps=2).recommend(["66VCHSJNUP"])

    assert model.calls[1]["tools"] == FINAL_TOOLS
    assert decision.outcome == "agent"


def test_step_limit_without_answer_falls_back(catalog, clock):
    model = ScriptedModel(tool_turn("search_catalog", query="kitchen"), tool_turn("search_catalog", query="kitchen"))
    decision = make_agent(catalog, model, clock, max_steps=2).recommend([])

    assert decision.outcome == "fallback"
    assert "after 2 steps" in decision.fallback_reason


def test_plain_text_answer_with_ids_is_accepted(catalog, clock):
    model = ScriptedModel(ModelTurn(content="I suggest 9SIQT8TOJO, then 6E92ZMYYFZ and L9ECAV7KIM."))
    decision = make_agent(catalog, model, clock).recommend(["LS4PSXUNUM"])

    assert decision.outcome == "agent"
    assert decision.product_ids[:3] == ["9SIQT8TOJO", "6E92ZMYYFZ", "L9ECAV7KIM"]


def test_single_id_string_is_accepted(catalog, clock):
    model = ScriptedModel(tool_turn("recommend", product_ids="6E92ZMYYFZ"))
    decision = make_agent(catalog, model, clock).recommend(["LS4PSXUNUM"])

    assert decision.outcome == "agent"
    assert decision.product_ids[0] == "6E92ZMYYFZ"


def test_no_model_configured_uses_v1(catalog, clock):
    decision = make_agent(catalog, None, clock).recommend(["66VCHSJNUP"])

    assert decision.outcome == "fallback"
    assert "no model configured" in decision.fallback_reason
    assert_v1_contract(decision, ["66VCHSJNUP"])


def test_repeat_context_is_served_from_cache(catalog, clock):
    model = ScriptedModel(tool_turn("recommend", product_ids=["6E92ZMYYFZ", "9SIQT8TOJO"], reason="Kitchen set."))
    agent = make_agent(catalog, model, clock, cache_ttl_seconds=600)

    first = agent.recommend(["LS4PSXUNUM"])
    second = agent.recommend(["LS4PSXUNUM"])

    assert len(model.calls) == 1
    assert first.outcome == "agent"
    assert second.outcome == "cached"
    assert second.product_ids[:2] == ["6E92ZMYYFZ", "9SIQT8TOJO"]
    assert second.reason == "Kitchen set."
    assert second.prompt_tokens == 0


def test_cache_expires(catalog, clock):
    model = ScriptedModel(
        tool_turn("recommend", product_ids=["6E92ZMYYFZ"]),
        tool_turn("recommend", product_ids=["9SIQT8TOJO"]),
    )
    agent = make_agent(catalog, model, clock, cache_ttl_seconds=60)

    agent.recommend(["LS4PSXUNUM"])
    clock.advance(61)
    decision = agent.recommend(["LS4PSXUNUM"])

    assert decision.outcome == "agent"
    assert decision.product_ids[0] == "9SIQT8TOJO"


def test_sanitize_respects_limit_and_order():
    catalog_ids = set(PRODUCTS)
    proposed = ["6E92ZMYYFZ", "9SIQT8TOJO", "LS4PSXUNUM", "L9ECAV7KIM", "1YMWWN1N4O", "66VCHSJNUP"]
    assert sanitize(proposed, catalog_ids, set(), 3) == proposed[:3]
