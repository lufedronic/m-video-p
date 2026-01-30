"""
OpenAI LLM provider implementation.
"""
import os
from typing import Optional

import openai

from .base import LLMProvider, LLMResponse, Message


class OpenAIProvider(LLMProvider):
    """LLM provider using OpenAI models."""

    MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "o1",
        "o1-mini",
        "o3-mini",
    ]

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = openai.OpenAI(api_key=api_key)

    @property
    def name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return "gpt-4o"

    @property
    def available_models(self) -> list[str]:
        return self.MODELS

    def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        thinking: bool = False,
        max_tokens: int = 8192,
        **kwargs
    ) -> LLMResponse:
        """
        Send a chat request to OpenAI.

        Args:
            messages: Conversation messages
            model: Model to use
            temperature: Sampling temperature
            thinking: Use reasoning model (o1/o3) if True
            max_tokens: Maximum tokens in response
        """
        model = model or self.default_model

        # If thinking requested and using a non-reasoning model, switch to o1
        if thinking and model.startswith("gpt-"):
            model = "o1"

        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content
            })

        try:
            # o1/o3 models don't support temperature or system messages the same way
            is_reasoning_model = model.startswith("o1") or model.startswith("o3")

            request_kwargs = {
                "model": model,
                "messages": openai_messages,
            }

            if is_reasoning_model:
                # Reasoning models use max_completion_tokens
                request_kwargs["max_completion_tokens"] = max_tokens
            else:
                request_kwargs["max_tokens"] = max_tokens
                request_kwargs["temperature"] = temperature

            response = self.client.chat.completions.create(**request_kwargs)

            result_text = response.choices[0].message.content or ""

            # o1/o3 models include reasoning in the response (not separately accessible)
            # The thinking is embedded in the response

            return LLMResponse(
                content=result_text,
                model=model,
                provider=self.name,
                thinking=None  # OpenAI doesn't expose reasoning separately
            )

        except Exception as e:
            return LLMResponse(
                content="",
                model=model,
                provider=self.name,
                error=str(e)
            )
