"""Tests for LLM provider abstraction and service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.llm.providers.base import LLMMessage, LLMProvider, LLMResponse
from services.llm.providers.openai_provider import OpenAILLMProvider
from services.llm.providers.gemini_provider import GeminiLLMProvider
from services.llm.providers.factory import create_llm_provider
from services.llm.service import LLMService
from config.settings import Settings


@pytest.mark.asyncio
class TestOpenAILLMProvider:
    @pytest.fixture
    def mock_openai(self):
        with patch("services.llm.providers.openai_provider.AsyncOpenAI") as mock:
            client = mock.return_value
            client.chat = MagicMock()
            client.chat.completions = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Hello!"))]
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
            client.chat.completions.create = AsyncMock(return_value=mock_response)
            yield mock

    @pytest.mark.asyncio
    async def test_complete(self, mock_openai):
        provider = OpenAILLMProvider(api_key="test-key")
        messages = [LLMMessage(role="user", content="Hi")]
        result = await provider.complete(messages)
        assert isinstance(result, LLMResponse)
        assert result.content == "Hello!"
        assert "prompt_tokens" in result.usage

    def test_model_name(self, mock_openai):
        provider = OpenAILLMProvider(api_key="test-key", model="gpt-4o-mini")
        assert provider.model_name == "gpt-4o-mini"


@pytest.mark.asyncio
class TestGeminiLLMProvider:
    @pytest.fixture
    def mock_genai(self):
        with patch("services.llm.providers.gemini_provider.genai") as mock:
            client = MagicMock()
            mock.Client.return_value = client
            client.aio = MagicMock()
            client.aio.models = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Hello!"
            mock_response.usage_metadata = MagicMock(
                prompt_token_count=10, candidates_token_count=5
            )
            client.aio.models.generate_content = AsyncMock(return_value=mock_response)
            yield mock

    @pytest.mark.asyncio
    async def test_complete(self, mock_genai):
        provider = GeminiLLMProvider(api_key="test-key")
        messages = [LLMMessage(role="user", content="Hi")]
        result = await provider.complete(messages)
        assert result.content == "Hello!"

    def test_model_name(self, mock_genai):
        provider = GeminiLLMProvider(api_key="test-key", model="gemini-2.0-flash")
        assert provider.model_name == "gemini-2.0-flash"


class TestCreateLLMProvider:
    def test_openai_factory(self):
        s = Settings(AI_PROVIDER="openai", OPENAI_API_KEY="sk-test", GEMINI_API_KEY="")
        provider = create_llm_provider(s)
        assert isinstance(provider, OpenAILLMProvider)

    def test_gemini_factory(self):
        s = Settings(AI_PROVIDER="gemini", GEMINI_API_KEY="test-key", OPENAI_API_KEY="")
        provider = create_llm_provider(s)
        assert isinstance(provider, GeminiLLMProvider)


@pytest.mark.asyncio
class TestLLMService:
    @pytest.fixture
    def mock_provider(self):
        provider = AsyncMock(spec=LLMProvider)
        provider.complete = AsyncMock(
            return_value=LLMResponse(content="Summary text", model="test", usage={})
        )
        provider.model_name = "test-model"
        return provider

    @pytest.mark.asyncio
    async def test_generate(self, mock_provider):
        service = LLMService(provider=mock_provider)
        result = await service.generate("You are a helper", "Hello")
        assert result == "Summary text"
        mock_provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize(self, mock_provider):
        service = LLMService(provider=mock_provider)
        result = await service.summarize("Long text to summarize")
        assert result == "Summary text"
