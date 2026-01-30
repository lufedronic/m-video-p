"""
Anthropic Claude LLM provider implementation.
"""
import os
from typing import Optional

import anthropic

from .base import LLMProvider, LLMResponse, Message


class AnthropicProvider(LLMProvider):
    """LLM provider using Anthropic Claude models."""

    MODELS = [
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ]

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = anthropic.Anthropic(api_key=api_key)

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-20250514"

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
        Send a chat request to Claude.

        Args:
            messages: Conversation messages
            model: Model to use
            temperature: Sampling temperature
            thinking: Enable extended thinking mode
            max_tokens: Maximum tokens in response
        """
        model = model or self.default_model

        # Extract system message if present
        system_content = None
        claude_messages = []

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            elif msg.role in ("user", "assistant"):
                claude_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        try:
            # Build request kwargs
            request_kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": claude_messages,
            }

            if system_content:
                request_kwargs["system"] = system_content

            # Handle extended thinking for Claude
            if thinking:
                # Extended thinking requires specific budget and temperature
                request_kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": 10000
                }
                # Extended thinking requires temperature = 1
                request_kwargs["temperature"] = 1.0
            else:
                request_kwargs["temperature"] = temperature

            response = self.client.messages.create(**request_kwargs)

            # Extract text and thinking from response
            result_text = ""
            thinking_text = ""

            for block in response.content:
                if block.type == "thinking":
                    thinking_text += block.thinking
                elif block.type == "text":
                    result_text += block.text

            return LLMResponse(
                content=result_text,
                model=model,
                provider=self.name,
                thinking=thinking_text if thinking_text else None
            )

        except Exception as e:
            return LLMResponse(
                content="",
                model=model,
                provider=self.name,
                error=str(e)
            )
