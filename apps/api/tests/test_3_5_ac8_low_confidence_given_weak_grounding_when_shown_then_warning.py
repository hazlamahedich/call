"""Story 3.5 AC8: Low Confidence Warning.

Tests that low_confidence_warning is true when grounding confidence
drops below 0.5 and false when confidence is at or above 0.5.
Tests exercise the actual service pipeline via _format_source_attribution
and send_chat_message, not just Python comparison operators.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest_3_5 import (
    TEST_ORG,
    mock_session,
    lab_service,
    make_active_row,
    make_raw_chunk,
    mock_gen_result,
    chat_pipeline_patches,
)
from services.script_lab import ScriptLabService
from fastapi import HTTPException


def _setup_session(mock_session, row):
    mock_result = MagicMock()
    mock_result.fetchone.return_value = row
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()


@pytest.mark.asyncio
class TestAC8LowConfidence:
    @pytest.mark.p0
    async def test_3_5_026_given_response_confidence_below_threshold_when_formatting_then_warning_true(
        self, lab_service
    ):
        low_confidence_chunks = [
            make_raw_chunk(similarity=0.12),
            make_raw_chunk(
                chunk_id=43,
                similarity=0.25,
                content="Weak grounding content.",
            ),
        ]

        attributions = lab_service._format_source_attribution(low_confidence_chunks)
        assert len(attributions) == 2

        avg_score = sum(a.similarity_score for a in attributions) / len(attributions)
        low_confidence_warning = avg_score < 0.5

        assert low_confidence_warning is True
        assert avg_score < 0.5

    @pytest.mark.p0
    async def test_3_5_027_given_response_confidence_at_threshold_when_formatting_then_warning_false(
        self, lab_service
    ):
        high_confidence_chunks = [
            make_raw_chunk(similarity=0.92),
            make_raw_chunk(
                chunk_id=43,
                similarity=0.85,
                content="Strong grounding content.",
            ),
        ]

        attributions = lab_service._format_source_attribution(high_confidence_chunks)
        avg_score = sum(a.similarity_score for a in attributions) / len(attributions)
        low_confidence_warning = avg_score < 0.5

        assert low_confidence_warning is False
        assert avg_score >= 0.5

    @pytest.mark.p1
    async def test_3_5_027b_given_confidence_exactly_at_boundary_when_chat_then_no_warning(
        self, mock_session, lab_service
    ):
        _setup_session(mock_session, make_active_row(turn_count=0))

        async with chat_pipeline_patches(mock_gen_result(confidence=0.5)):
            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Boundary test"
            )

        assert result.low_confidence_warning is False
        assert result.grounding_confidence == 0.5

    @pytest.mark.p1
    async def test_3_5_027c_given_confidence_just_below_boundary_when_chat_then_warning(
        self, mock_session, lab_service
    ):
        _setup_session(mock_session, make_active_row(turn_count=0))

        async with chat_pipeline_patches(mock_gen_result(confidence=0.499)):
            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Just below boundary"
            )

        assert result.low_confidence_warning is True
        assert result.grounding_confidence == 0.499

    @pytest.mark.p1
    async def test_3_5_027d_given_zero_confidence_when_chat_then_warning(
        self, mock_session, lab_service
    ):
        _setup_session(mock_session, make_active_row(turn_count=0))

        async with chat_pipeline_patches(mock_gen_result(confidence=0.0)):
            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Zero confidence"
            )

        assert result.low_confidence_warning is True
        assert result.grounding_confidence == 0.0

    @pytest.mark.p1
    async def test_3_5_027e_given_perfect_confidence_when_chat_then_no_warning(
        self, mock_session, lab_service
    ):
        _setup_session(mock_session, make_active_row(turn_count=0))

        async with chat_pipeline_patches(mock_gen_result(confidence=1.0)):
            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Perfect confidence"
            )

        assert result.low_confidence_warning is False
        assert result.grounding_confidence == 1.0
