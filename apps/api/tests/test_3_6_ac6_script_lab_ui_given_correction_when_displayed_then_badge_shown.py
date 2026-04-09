"""AC6: Script Lab UI correction metadata serialization tests."""

import pytest

from schemas.script_lab import LabChatResponse
from schemas.factual_hook import ClaimVerificationResponse


@pytest.mark.asyncio
class TestScriptLabUI:
    async def test_3_6_unit_020_given_corrected_when_serialized_then_camel_case_json(
        self,
    ):
        resp = LabChatResponse(
            response_text="Our revenue grew 32% in Q3.",
            source_attributions=[],
            grounding_confidence=0.9,
            turn_number=1,
            low_confidence_warning=False,
            was_corrected=True,
            correction_count=2,
            verification_timed_out=False,
            verified_claims=[
                ClaimVerificationResponse(
                    claim_text="Revenue grew 32%",
                    is_supported=True,
                    max_similarity=0.88,
                ),
                ClaimVerificationResponse(
                    claim_text="Unknown claim",
                    is_supported=False,
                    max_similarity=0.3,
                    verification_error=True,
                ),
            ],
        )
        data = resp.model_dump(by_alias=True)
        assert data["wasCorrected"] is True
        assert data["correctionCount"] == 2
        assert data["verificationTimedOut"] is False
        assert len(data["verifiedClaims"]) == 2
        assert data["verifiedClaims"][0]["claimText"] == "Revenue grew 32%"
        assert data["verifiedClaims"][0]["isSupported"] is True
        assert data["verifiedClaims"][1]["isSupported"] is False
        assert data["verifiedClaims"][1]["verificationError"] is True

    async def test_3_6_unit_020b_given_no_correction_when_serialized_then_defaults(
        self,
    ):
        resp = LabChatResponse(
            response_text="Hello!",
            source_attributions=[],
            grounding_confidence=0.7,
            turn_number=1,
            low_confidence_warning=False,
        )
        data = resp.model_dump(by_alias=True)
        assert data["wasCorrected"] is False
        assert data["correctionCount"] == 0
        assert data["verifiedClaims"] == []
