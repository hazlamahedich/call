"""Shared fixtures for Story 3.6 factual hook tests."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.factual_hook import (
    ClaimVerification,
    FactualHookResult,
    FactualHookService,
)


def make_claim_verification(
    claim_text: str = "Our revenue grew 32% in Q3.",
    is_supported: bool = True,
    max_similarity: float = 0.85,
    verification_error: bool = False,
) -> ClaimVerification:
    chunks = (
        [{"chunk_id": 1, "content": "Revenue grew 32%", "similarity": max_similarity}]
        if is_supported
        else []
    )
    return ClaimVerification(
        claim_text=claim_text,
        is_supported=is_supported,
        supporting_chunks=chunks,
        max_similarity=max_similarity,
        verification_error=verification_error,
    )


def make_factual_hook_result(
    was_corrected: bool = False,
    correction_count: int = 0,
    final_response: str = "response",
    original_response: str = "response",
    verified_claims: list[ClaimVerification] | None = None,
    verification_timed_out: bool = False,
    total_verification_ms: float = 10.0,
    circuit_breaker_open: bool = False,
) -> FactualHookResult:
    return FactualHookResult(
        was_corrected=was_corrected,
        correction_count=correction_count,
        final_response=final_response,
        original_response=original_response,
        verified_claims=verified_claims or [],
        verification_timed_out=verification_timed_out,
        total_verification_ms=total_verification_ms,
        circuit_breaker_open=circuit_breaker_open,
    )


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(
        return_value="Corrected response with supported claims only."
    )
    return llm


@pytest.fixture
def mock_embedding():
    emb = AsyncMock()
    emb.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    return emb


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def factual_hook_service(mock_session, mock_llm, mock_embedding):
    svc = FactualHookService(mock_session, mock_llm, mock_embedding)
    FactualHookService._consecutive_errors = 0
    FactualHookService._circuit_open = False
    FactualHookService._circuit_opened_at = 0.0
    yield svc
    FactualHookService._consecutive_errors = 0
    FactualHookService._circuit_open = False
    FactualHookService._circuit_opened_at = 0.0
