"""
Base abstraction for LLM providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class Message:
    """A single message in a conversation."""
    role: str  # "user", "assistant", or "system"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    provider: str
    thinking: Optional[str] = None  # For models that support thinking/reasoning
    error: Optional[str] = None
    # Token usage fields
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    thinking_tokens: Optional[int] = None
    finish_reason: Optional[str] = None

    def is_success(self) -> bool:
        return self.error is None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier (e.g., 'gemini', 'anthropic', 'openai')."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model for this provider."""
        pass

    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """List of available models for this provider."""
        pass

    def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        thinking: bool = False,
        **kwargs
    ) -> LLMResponse:
        """
        Send a chat completion request with automatic tracing.

        Args:
            messages: List of conversation messages
            model: Model to use (defaults to provider's default)
            temperature: Sampling temperature (0.0-1.0)
            thinking: Enable thinking/reasoning mode if supported
            **kwargs: Provider-specific options

        Returns:
            LLMResponse with the model's response
        """
        model = model or self.default_model

        try:
            from llm_trace import llm_trace

            with llm_trace(
                provider=self.name,
                model=model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                thinking_enabled=thinking,
                extra_params=kwargs
            ) as trace:
                response = self._chat_impl(messages, model, temperature, thinking, **kwargs)
                trace.record_response(
                    output=response.content,
                    thinking=response.thinking,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    status="error" if response.error else "success",
                    error_message=response.error,
                    finish_reason=response.finish_reason
                )
                return response
        except ImportError:
            # llm_trace not installed, call directly without tracing
            return self._chat_impl(messages, model, temperature, thinking, **kwargs)

    @abstractmethod
    def _chat_impl(
        self,
        messages: list[Message],
        model: str,
        temperature: float,
        thinking: bool,
        **kwargs
    ) -> LLMResponse:
        """
        Internal implementation of chat. Subclasses must implement this.

        Args:
            messages: List of conversation messages
            model: Model to use (already resolved to actual model name)
            temperature: Sampling temperature (0.0-1.0)
            thinking: Enable thinking/reasoning mode if supported
            **kwargs: Provider-specific options

        Returns:
            LLMResponse with the model's response
        """
        pass

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        thinking: bool = False,
        **kwargs
    ) -> LLMResponse:
        """
        Simple single-turn generation.

        Args:
            prompt: The prompt to send
            model: Model to use (defaults to provider's default)
            temperature: Sampling temperature
            thinking: Enable thinking mode if supported

        Returns:
            LLMResponse with the model's response
        """
        messages = [Message(role="user", content=prompt)]
        return self.chat(messages, model=model, temperature=temperature, thinking=thinking, **kwargs)
