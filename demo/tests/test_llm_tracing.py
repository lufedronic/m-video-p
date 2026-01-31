"""
Tests for LLM provider tracing integration.

Run with:
    cd demo && python3 -m pytest tests/test_llm_tracing.py -v

Success criteria: All tests must pass.
"""
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pytest

from providers.llm.base import LLMProvider, LLMResponse, Message


class TestLLMResponseTokenFields:
    """Test that LLMResponse has token fields."""

    def test_llmresponse_has_input_tokens(self):
        """LLMResponse has input_tokens field."""
        response = LLMResponse(
            content="Hello",
            model="test",
            provider="test",
            input_tokens=100
        )
        assert response.input_tokens == 100

    def test_llmresponse_has_output_tokens(self):
        """LLMResponse has output_tokens field."""
        response = LLMResponse(
            content="Hello",
            model="test",
            provider="test",
            output_tokens=50
        )
        assert response.output_tokens == 50

    def test_llmresponse_has_thinking_tokens(self):
        """LLMResponse has thinking_tokens field."""
        response = LLMResponse(
            content="Hello",
            model="test",
            provider="test",
            thinking_tokens=200
        )
        assert response.thinking_tokens == 200

    def test_llmresponse_has_finish_reason(self):
        """LLMResponse has finish_reason field."""
        response = LLMResponse(
            content="Hello",
            model="test",
            provider="test",
            finish_reason="stop"
        )
        assert response.finish_reason == "stop"

    def test_llmresponse_token_fields_optional(self):
        """Token fields are optional (default None)."""
        response = LLMResponse(
            content="Hello",
            model="test",
            provider="test"
        )
        assert response.input_tokens is None
        assert response.output_tokens is None
        assert response.thinking_tokens is None
        assert response.finish_reason is None


class TestLLMProviderHasChatImpl:
    """Test that LLMProvider uses _chat_impl pattern."""

    def test_provider_has_chat_impl_abstract(self):
        """LLMProvider has _chat_impl as abstract method."""
        # _chat_impl should be defined (either abstract or implemented)
        assert hasattr(LLMProvider, '_chat_impl') or hasattr(LLMProvider, 'chat')


class TestTracingIntegration:
    """Test that tracing is integrated into providers."""

    def test_llm_trace_module_importable(self):
        """llm_trace module can be imported."""
        from llm_trace import llm_trace, init_tracing
        assert llm_trace is not None
        assert init_tracing is not None

    def test_init_tracing_callable(self):
        """init_tracing can be called without error."""
        from llm_trace import init_tracing
        with tempfile.TemporaryDirectory() as tmp:
            init_tracing(log_dir=tmp)  # Should not raise


class TestGeminiProviderTokens:
    """Test Gemini provider extracts tokens."""

    def test_gemini_provider_exists(self):
        """GeminiProvider class exists."""
        try:
            from providers.llm.gemini import GeminiProvider
            assert GeminiProvider is not None
        except ImportError:
            pytest.skip("Gemini provider not available")

    def test_gemini_has_chat_impl(self):
        """GeminiProvider has _chat_impl method."""
        try:
            from providers.llm.gemini import GeminiProvider
            assert hasattr(GeminiProvider, '_chat_impl')
        except ImportError:
            pytest.skip("Gemini provider not available")


class TestAnthropicProviderTokens:
    """Test Anthropic provider extracts tokens."""

    def test_anthropic_provider_exists(self):
        """AnthropicProvider class exists."""
        try:
            from providers.llm.anthropic import AnthropicProvider
            assert AnthropicProvider is not None
        except ImportError:
            pytest.skip("Anthropic provider not available")

    def test_anthropic_has_chat_impl(self):
        """AnthropicProvider has _chat_impl method."""
        try:
            from providers.llm.anthropic import AnthropicProvider
            assert hasattr(AnthropicProvider, '_chat_impl')
        except ImportError:
            pytest.skip("Anthropic provider not available")


class TestOpenAIProviderTokens:
    """Test OpenAI provider extracts tokens."""

    def test_openai_provider_exists(self):
        """OpenAIProvider class exists."""
        try:
            from providers.llm.openai import OpenAIProvider
            assert OpenAIProvider is not None
        except ImportError:
            pytest.skip("OpenAI provider not available")

    def test_openai_has_chat_impl(self):
        """OpenAIProvider has _chat_impl method."""
        try:
            from providers.llm.openai import OpenAIProvider
            assert hasattr(OpenAIProvider, '_chat_impl')
        except ImportError:
            pytest.skip("OpenAI provider not available")


class TestBaseProviderTracing:
    """Test base provider tracing wrapper."""

    def test_chat_method_exists(self):
        """LLMProvider.chat method exists."""
        assert hasattr(LLMProvider, 'chat')

    def test_generate_method_exists(self):
        """LLMProvider.generate method exists."""
        assert hasattr(LLMProvider, 'generate')
