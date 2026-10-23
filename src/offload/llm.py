"""Thin model-client layer.

Everything that calls a model goes through `LLM`, so tests and evals can swap in recorded responses
(`ScriptedLLM`) without network access or an API key.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLM(Protocol):
    def parse(
        self,
        *,
        model: str,
        system: str,
        content: Sequence[dict],
        output_model: type[T],
        max_tokens: int = 4096,
    ) -> T:
        """One-shot call returning a validated structured object."""

    def create(self, **kwargs: Any) -> Any:
        """Raw Messages API call (used by the computer-use loop)."""


class AnthropicLLM:
    """Production client. Uses structured outputs so the response always matches the schema."""

    def __init__(self, client: Any | None = None) -> None:
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self._client = client

    def parse(self, *, model, system, content, output_model, max_tokens=4096):
        response = self._client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": list(content)}],
            output_format=output_model,
        )
        parsed = response.parsed_output
        if parsed is None:
            raise RuntimeError(f"model returned no parsable output (stop_reason={response.stop_reason})")
        return parsed

    def create(self, **kwargs):
        return self._client.messages.create(**kwargs)


class ScriptedLLM:
    """Test double. `parse` answers from a queue (or a function of the request); `create` likewise."""

    def __init__(
        self,
        parse_responses: Sequence[BaseModel | Callable[[dict], BaseModel]] = (),
        create_responses: Sequence[Any] = (),
    ) -> None:
        self._parse = list(parse_responses)
        self._create = list(create_responses)
        self.calls: list[dict] = []

    def parse(self, *, model, system, content, output_model, max_tokens=4096):
        request = {"model": model, "system": system, "content": list(content), "output_model": output_model}
        self.calls.append(request)
        if not self._parse:
            raise AssertionError(f"ScriptedLLM: no scripted response left for {output_model.__name__}")
        nxt = self._parse.pop(0)
        result = nxt(request) if callable(nxt) and not isinstance(nxt, BaseModel) else nxt
        if not isinstance(result, output_model):
            raise AssertionError(f"ScriptedLLM: expected {output_model.__name__}, got {type(result).__name__}")
        return result

    def create(self, **kwargs):
        import copy

        self.calls.append(copy.deepcopy(kwargs))  # snapshot: callers keep mutating their message list
        if not self._create:
            raise AssertionError("ScriptedLLM: no scripted create() response left")
        nxt = self._create.pop(0)
        return nxt(kwargs) if callable(nxt) else nxt
