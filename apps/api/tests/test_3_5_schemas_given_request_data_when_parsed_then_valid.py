"""Story 3.5: Schema Validation Tests.

Tests for LabChatRequest, ScenarioOverlayRequest, and CreateLabSessionRequest
schema validation including boundary conditions and camelCase aliasing.
"""

import sys
from pathlib import Path

import pydantic
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest_3_5 import (
    mock_session,
    lab_service,
)
from schemas.script_lab import (
    CreateLabSessionRequest,
    LabChatRequest,
    LabChatResponse,
    LabSessionResponse,
    ScenarioOverlayRequest,
    SourceAttribution,
)


class TestSchemaValidation:
    @pytest.mark.p0
    def test_3_5_schema_001_given_empty_message_when_parsed_then_rejected(self):
        with pytest.raises(pydantic.ValidationError) as exc_info:
            LabChatRequest(message="")
        errors = exc_info.value.errors()
        assert any("min_length" in str(e) for e in errors)

    @pytest.mark.p0
    def test_3_5_schema_002_given_message_over_max_length_when_parsed_then_rejected(
        self,
    ):
        with pytest.raises(pydantic.ValidationError) as exc_info:
            LabChatRequest(message="A" * 2001)
        errors = exc_info.value.errors()
        assert any("max_length" in str(e) for e in errors)

    @pytest.mark.p0
    def test_3_5_schema_003_given_message_at_max_length_when_parsed_then_valid(self):
        req = LabChatRequest(message="A" * 2000)
        assert len(req.message) == 2000

    @pytest.mark.p0
    def test_3_5_schema_004_given_message_single_char_when_parsed_then_valid(self):
        req = LabChatRequest(message="X")
        assert req.message == "X"

    @pytest.mark.p0
    def test_3_5_schema_005_given_empty_overlay_when_parsed_then_rejected(self):
        with pytest.raises(pydantic.ValidationError) as exc_info:
            ScenarioOverlayRequest(overlay={})
        errors = exc_info.value.errors()
        assert any("min_length" in str(e) for e in errors)

    @pytest.mark.p0
    def test_3_5_schema_006_given_overlay_with_over_20_keys_when_parsed_then_rejected(
        self,
    ):
        big_overlay = {f"key_{i}": f"val_{i}" for i in range(21)}
        with pytest.raises(pydantic.ValidationError) as exc_info:
            ScenarioOverlayRequest(overlay=big_overlay)
        errors = exc_info.value.errors()
        assert any("max_length" in str(e) for e in errors)

    @pytest.mark.p0
    def test_3_5_schema_007_given_overlay_with_exactly_20_keys_when_parsed_then_valid(
        self,
    ):
        overlay = {f"key_{i}": f"val_{i}" for i in range(20)}
        req = ScenarioOverlayRequest(overlay=overlay)
        assert len(req.overlay) == 20

    @pytest.mark.p0
    def test_3_5_schema_008_given_lab_chat_request_camel_alias_when_parsed_then_valid(
        self,
    ):
        req = LabChatRequest.model_validate({"message": "hello"})
        assert req.message == "hello"

    @pytest.mark.p0
    def test_3_5_schema_009_given_create_session_request_camel_alias_when_parsed_then_valid(
        self,
    ):
        req = CreateLabSessionRequest.model_validate(
            {"agentId": 1, "scriptId": 2, "leadId": 3}
        )
        assert req.agent_id == 1
        assert req.script_id == 2
        assert req.lead_id == 3

    @pytest.mark.p0
    def test_3_5_schema_010_given_create_session_without_lead_when_parsed_then_valid(
        self,
    ):
        req = CreateLabSessionRequest(agent_id=1, script_id=2)
        assert req.lead_id is None

    @pytest.mark.p1
    def test_3_5_schema_011_given_source_attribution_when_serialized_then_camel_case(
        self,
    ):
        sa = SourceAttribution(
            chunk_id=1,
            document_name="test.pdf",
            page_number=2,
            excerpt="excerpt text",
            similarity_score=0.9,
        )
        dumped = sa.model_dump(by_alias=True)
        assert "chunkId" in dumped
        assert "documentName" in dumped
        assert "pageNumber" in dumped
        assert "similarityScore" in dumped

    @pytest.mark.p1
    def test_3_5_schema_012_given_lab_chat_response_when_serialized_then_camel_case(
        self,
    ):
        resp = LabChatResponse(
            response_text="Hello",
            source_attributions=[],
            grounding_confidence=0.8,
            turn_number=1,
            low_confidence_warning=False,
        )
        dumped = resp.model_dump(by_alias=True)
        assert "responseText" in dumped
        assert "sourceAttributions" in dumped
        assert "groundingConfidence" in dumped
        assert "turnNumber" in dumped
        assert "lowConfidenceWarning" in dumped

    @pytest.mark.p1
    def test_3_5_schema_013_given_lab_session_response_when_serialized_then_camel_case(
        self,
    ):
        resp = LabSessionResponse(
            session_id=1,
            agent_id=1,
            script_id=1,
            lead_id=None,
            status="active",
            expires_at="2026-01-01T00:00:00",
            scenario_overlay=None,
        )
        dumped = resp.model_dump(by_alias=True)
        assert "sessionId" in dumped
        assert "agentId" in dumped
        assert "scriptId" in dumped
        assert "leadId" in dumped
        assert "expiresAt" in dumped
        assert "scenarioOverlay" in dumped

    @pytest.mark.p1
    def test_3_5_schema_014_given_scenario_overlay_request_camel_alias_when_parsed_then_valid(
        self,
    ):
        req = ScenarioOverlayRequest.model_validate({"overlay": {"name": "Acme"}})
        assert req.overlay["name"] == "Acme"
