"""LLM backend adapters — model-agnostic design."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    model: str


# Token pricing per million tokens (USD)
PRICING = {
    # Anthropic
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6-20260320": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6-20260319": {"input": 15.00, "output": 75.00},
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "o3-mini": {"input": 1.10, "output": 4.40},
    # Google
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD."""
    # Find matching pricing (partial match)
    for key, prices in PRICING.items():
        if key in model or model in key:
            return (
                input_tokens * prices["input"] / 1_000_000
                + output_tokens * prices["output"] / 1_000_000
            )
    return 0.0  # Unknown model


class LLMBackend(ABC):
    """Abstract LLM backend."""

    @abstractmethod
    def chat(self, system: str, user: str) -> LLMResponse:
        """Send a single message and get a response. Each call = isolated session."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


class AnthropicBackend(LLMBackend):
    def __init__(self, model: str = "claude-sonnet-4-6-20260320"):
        import anthropic
        self._client = anthropic.Anthropic()
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, system: str, user: str) -> LLMResponse:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return LLMResponse(
            content=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self._model,
        )


class OpenAIBackend(LLMBackend):
    def __init__(self, model: str = "gpt-4o"):
        from openai import OpenAI
        self._client = OpenAI()
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, system: str, user: str) -> LLMResponse:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            model=self._model,
        )


def create_backend(provider: str = "anthropic", model: str | None = None) -> LLMBackend:
    """Factory for LLM backends."""
    if provider == "anthropic":
        return AnthropicBackend(model or "claude-sonnet-4-6-20260320")
    elif provider == "openai":
        return OpenAIBackend(model or "gpt-4o")
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'anthropic' or 'openai'.")
