"""Tests for embedding provider abstraction."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.embedding.providers.base import EmbeddingProvider
from services.embedding.providers.openai_provider import OpenAIEmbeddingProvider
from services.embedding.providers.gemini_provider import GeminiEmbeddingProvider
from services.embedding.providers.factory import create_embedding_provider
from config.settings import Settings


@pytest.mark.asyncio
class TestOpenAIEmbeddingProvider:
    @pytest.fixture
    def mock_openai(self):
        with patch("services.embedding.providers.openai_provider.AsyncOpenAI") as mock:
            client = mock.return_value
            client.embeddings = MagicMock()
            client.embeddings.create = AsyncMock(
                return_value=MagicMock(data=[MagicMock(embedding=[0.1] * 1536)])
            )
            yield mock

    @pytest.mark.asyncio
    async def test_embed_single(self, mock_openai):
        provider = OpenAIEmbeddingProvider(api_key="test-key")
        result = await provider.embed("test text")
        assert len(result) == 1536

    @pytest.mark.asyncio
    async def test_embed_batch(self, mock_openai):
        mock_openai.return_value.embeddings.create = AsyncMock(
            return_value=MagicMock(
                data=[
                    MagicMock(embedding=[0.1] * 1536),
                    MagicMock(embedding=[0.2] * 1536),
                ]
            )
        )
        provider = OpenAIEmbeddingProvider(api_key="test-key")
        result = await provider.embed_batch(["text1", "text2"])
        assert len(result) == 2

    def test_model_name(self, mock_openai):
        provider = OpenAIEmbeddingProvider(
            api_key="test-key", model="text-embedding-3-small"
        )
        assert provider.model_name == "text-embedding-3-small"

    def test_dimensions(self, mock_openai):
        provider = OpenAIEmbeddingProvider(api_key="test-key", dimensions=1536)
        assert provider.dimensions == 1536


@pytest.mark.asyncio
class TestGeminiEmbeddingProvider:
    @pytest.fixture
    def mock_genai(self):
        with patch("services.embedding.providers.gemini_provider.genai") as mock:
            client = MagicMock()
            mock.Client.return_value = client
            client.aio = MagicMock()
            client.aio.models = MagicMock()
            mock_response = MagicMock()
            mock_response.embeddings = [MagicMock(values=[0.1] * 3072)]
            client.aio.models.embed_content = AsyncMock(return_value=mock_response)
            yield mock

    @pytest.mark.asyncio
    async def test_embed_single(self, mock_genai):
        provider = GeminiEmbeddingProvider(api_key="test-key")
        result = await provider.embed("test text")
        assert len(result) == 3072

    @pytest.mark.asyncio
    async def test_embed_batch(self, mock_genai):
        mock_response = MagicMock()
        mock_response.embeddings = [
            MagicMock(values=[0.1] * 3072),
            MagicMock(values=[0.2] * 3072),
        ]
        mock_genai.Client.return_value.aio.models.embed_content = AsyncMock(
            return_value=mock_response
        )
        provider = GeminiEmbeddingProvider(api_key="test-key")
        result = await provider.embed_batch(["text1", "text2"])
        assert len(result) == 2

    def test_model_name(self, mock_genai):
        provider = GeminiEmbeddingProvider(
            api_key="test-key", model="gemini-embedding-001"
        )
        assert provider.model_name == "gemini-embedding-001"

    def test_dimensions(self, mock_genai):
        provider = GeminiEmbeddingProvider(api_key="test-key", dimensions=3072)
        assert provider.dimensions == 3072


class TestCreateEmbeddingProvider:
    def test_openai_factory(self):
        s = Settings(AI_PROVIDER="openai", OPENAI_API_KEY="sk-test", GEMINI_API_KEY="")
        provider = create_embedding_provider(s)
        assert isinstance(provider, OpenAIEmbeddingProvider)
        assert provider.model_name == "text-embedding-3-small"

    def test_gemini_factory(self):
        s = Settings(AI_PROVIDER="gemini", GEMINI_API_KEY="test-key", OPENAI_API_KEY="")
        provider = create_embedding_provider(s)
        assert isinstance(provider, GeminiEmbeddingProvider)
        assert provider.model_name == "gemini-embedding-001"
        assert provider.dimensions == 3072
