from unittest.mock import patch

from recommendation_agent.model import ChatModel
from recommendation_agent.tools import FINAL_TOOLS


def test_default_model_request_keeps_ollama_parameters():
    with patch("recommendation_agent.model.OpenAI") as client:
        model = ChatModel("http://ollama:11434/v1", "ollama", "qwen3:4b-instruct", 300)
        model.complete([], FINAL_TOOLS, timeout=2)

    request = client.return_value.chat.completions.create.call_args.kwargs
    assert request["tool_choice"] == "auto"
    assert request["max_tokens"] == 300
    assert "max_completion_tokens" not in request
    assert "reasoning_effort" not in request


def test_reasoning_model_uses_completion_token_limit_and_named_tool():
    tool_choice = {"type": "function", "function": {"name": "recommend"}}
    with patch("recommendation_agent.model.OpenAI") as client:
        model = ChatModel(
            "https://api.groq.com/openai/v1", "test-key", "openai/gpt-oss-20b",
            600, tool_choice=tool_choice, reasoning_effort="low",
        )
        model.complete([], FINAL_TOOLS, timeout=2)

    request = client.return_value.chat.completions.create.call_args.kwargs
    assert request["tool_choice"] == tool_choice
    assert request["max_completion_tokens"] == 600
    assert request["reasoning_effort"] == "low"
    assert "max_tokens" not in request
