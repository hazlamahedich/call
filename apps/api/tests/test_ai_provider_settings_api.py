"""Tests for AI provider settings API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.embedding.providers.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    async def embed(self, text, *, task_type="RETRIEVAL_DOCUMENT"):
        return [0.1] * 1536

    async def embed_batch(self, texts, *, task_type="RETRIEVAL_DOCUMENT"):
        return [[0.1] * 1536 for _ in texts]

    @property
    def model_name(self):
        return "mock-model"

    @property
    def dimensions(self):
        return 1536
