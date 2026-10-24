"""Chat model client.

ChatModel talks to any OpenAI-compatible chat completions API with tool
calling: a local Ollama server, Hugging Face Inference Providers, GitHub
Models and others differ only in base URL, key and model name. Anything with
the same `complete` method can be used instead, which is how the tests run
without network access.
"""

import json
from dataclasses import dataclass, field

from openai import OpenAI


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ModelTurn:
    content: str
    tool_calls: list = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def as_message(self):
        """The assistant message to append to the conversation history."""
        message = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
                }
                for call in self.tool_calls
            ]
        return message


def _parse_arguments(raw):
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


class ChatModel:
    def __init__(self, base_url, api_key, model, max_tokens):
        # Retries are disabled: the agent has its own deadline and falls back to v1.
        # Local servers such as Ollama ignore the key but the client requires one.
        self._client = OpenAI(api_key=api_key or "unused", base_url=base_url, max_retries=0)
        self.name = model
        self._max_tokens = max_tokens

    def complete(self, messages, tools, timeout):
        response = self._client.chat.completions.create(
            model=self.name,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2,
            max_tokens=self._max_tokens,
            timeout=timeout,
        )
        message = response.choices[0].message
        usage = response.usage
        return ModelTurn(
            content=message.content or "",
            tool_calls=[
                ToolCall(id=call.id, name=call.function.name, arguments=_parse_arguments(call.function.arguments))
                for call in (message.tool_calls or [])
            ],
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )
