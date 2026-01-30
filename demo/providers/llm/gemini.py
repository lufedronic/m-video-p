"""
Google Gemini LLM provider implementation.
"""
import os
from typing import Optional

from google import genai

from .base import LLMProvider, LLMResponse, Message


class GeminiProvider(LLMProvider):
    """LLM provider using Google Gemini models."""

    MODELS = [
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",
        "gemini-2.5-flash-preview-05-20",
        "gemini-2.5-pro-preview-05-06",
    ]

    THINKING_LEVELS = {
        "minimal": "minimal",
        "low": "low",
        "medium": "medium",
        "high": "high",
    }

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.client = genai.Client(api_key=api_key)

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-3-flash-preview"

    @property
    def available_models(self) -> list[str]:
        return self.MODELS

    def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        thinking: bool = False,
        thinking_level: str = "medium",
        **kwargs
    ) -> LLMResponse:
        """
        Send a chat request to Gemini.

        Args:
            messages: Conversation messages
            model: Model to use
            temperature: Sampling temperature
            thinking: Enable thinking mode
            thinking_level: Level of thinking (minimal/low/medium/high)
        """
        model = model or self.default_model

        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            if msg.role == "system":
                # Gemini doesn't have system role, prepend to first user message
                # or add as user message with model acknowledgment
                gemini_messages.append({
                    "role": "user",
                    "parts": [{"text": msg.content}]
                })
                gemini_messages.append({
                    "role": "model",
                    "parts": [{"text": "I understand. I'll follow these instructions."}]
                })
            elif msg.role == "user":
                gemini_messages.append({
                    "role": "user",
                    "parts": [{"text": msg.content}]
                })
            elif msg.role == "assistant":
                gemini_messages.append({
                    "role": "model",
                    "parts": [{"text": msg.content}]
                })

        # Build config
        config = {"temperature": temperature}

        if thinking:
            level = self.THINKING_LEVELS.get(thinking_level, "medium")
            config["thinking_config"] = {"thinking_level": level}

        try:
            response = self.client.models.generate_content(
                model=model,
                contents=gemini_messages,
                config=config
            )

            # Extract text and thinking from response
            result_text = ""
            thinking_text = ""

            for part in response.candidates[0].content.parts:
                if hasattr(part, 'thought') and part.thought:
                    thinking_text += part.text if hasattr(part, 'text') else ""
                elif hasattr(part, 'text') and part.text:
                    result_text += part.text

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
