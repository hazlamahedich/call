"""
Story 1-6: 10-Minute Launch Onboarding Wizard
Unit Tests for Onboarding Schema, Models, and Route Logic

Test ID Format: [1.6-UNIT-XXX]
Priority: P0 (Critical) | P1 (High) | P2 (Medium)
"""

import os
import re
from pathlib import Path

import pytest
from pydantic import ValidationError
from schemas.onboarding import OnboardingPayload


class TestOnboardingPayloadValidation:
    """[1.6-UNIT-001..006] OnboardingPayload schema validation"""

    def test_valid_payload(self):
        payload = OnboardingPayload(
            business_goal="Lead generation",
            script_context="We sell premium widgets to small businesses",
            voice_id="avery",
            integration_type="gohighlevel",
            safety_level="strict",
        )
        assert payload.business_goal == "Lead generation"
        assert payload.script_context == "We sell premium widgets to small businesses"
        assert payload.voice_id == "avery"
        assert payload.integration_type == "gohighlevel"
        assert payload.safety_level == "strict"

    def test_camel_case_alias(self):
        payload = OnboardingPayload(
            **{
                "businessGoal": "Lead generation",
                "scriptContext": "We sell premium widgets to small businesses",
                "voiceId": "avery",
                "integrationType": "gohighlevel",
                "safetyLevel": "strict",
            }
        )
        assert payload.business_goal == "Lead generation"
        assert payload.script_context == "We sell premium widgets to small businesses"

    def test_invalid_safety_level_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            OnboardingPayload(
                business_goal="Lead gen",
                script_context="A" * 20,
                voice_id="avery",
                safety_level="invalid",
            )
        errors = exc_info.value.errors()
        assert any("safety_level" in str(e) for e in errors)

    def test_valid_safety_levels(self):
        for level in ["strict", "moderate", "relaxed"]:
            payload = OnboardingPayload(
                business_goal="Lead gen",
                script_context="A" * 20,
                voice_id="avery",
                safety_level=level,
            )
            assert payload.safety_level == level

    def test_script_context_too_short_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            OnboardingPayload(
                business_goal="Lead gen",
                script_context="Too short",
                voice_id="avery",
                safety_level="strict",
            )
        errors = exc_info.value.errors()
        assert any("script_context" in str(e) for e in errors)

    def test_script_context_exactly_min_length_passes(self):
        payload = OnboardingPayload(
            business_goal="Lead gen",
            script_context="A" * 20,
            voice_id="avery",
            safety_level="strict",
        )
        assert len(payload.script_context) == 20

    def test_optional_integration_type(self):
        payload = OnboardingPayload(
            business_goal="Lead gen",
            script_context="A" * 20,
            voice_id="avery",
            safety_level="strict",
            integration_type=None,
        )
        assert payload.integration_type is None

    def test_missing_required_fields_rejected(self):
        with pytest.raises(ValidationError):
            OnboardingPayload()


class TestOnErrorCodesSync:
    """[1.6-UNIT-007..010] Verify ONBOARDING_ERROR_CODES in TypeScript constants"""

    _ROOT = Path(__file__).resolve().parent.parent.parent.parent

    def _extract_ts_const(self, file_path: Path, const_name: str) -> dict:
        content = file_path.read_text()
        pattern = rf"export const {const_name}\s*=\s*\{{([^}}]+)\}}"
        match = re.search(pattern, content)
        if not match:
            return {}
        body = match.group(1)
        result = {}
        for line in body.strip().split("\n"):
            line = line.strip().rstrip(",")
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                result[key] = value
        return result

    def test_onboarding_error_codes_exist_in_ts(self):
        ts_path = self._ROOT / "packages" / "constants" / "index.ts"
        codes = self._extract_ts_const(ts_path, "ONBOARDING_ERROR_CODES")
        assert codes, "ONBOARDING_ERROR_CODES not found in packages/constants/index.ts"
        assert "ONBOARDING_ALREADY_COMPLETE" in codes
        assert "ONBOARDING_VALIDATION_ERROR" in codes
        assert "ONBOARDING_CREATE_ERROR" in codes

    def test_onboarding_error_codes_values_match_keys(self):
        ts_path = self._ROOT / "packages" / "constants" / "index.ts"
        codes = self._extract_ts_const(ts_path, "ONBOARDING_ERROR_CODES")
        for key, value in codes.items():
            assert key == value, f"ONBOARDING_ERROR_CODES key {key} != value {value}"

    def test_onboarding_error_type_exported(self):
        ts_path = self._ROOT / "packages" / "constants" / "index.ts"
        content = ts_path.read_text()
        assert "OnboardingErrorCode" in content

    def test_router_uses_matching_error_codes(self):
        import routers.onboarding as onboarding_mod

        ts_path = self._ROOT / "packages" / "constants" / "index.ts"
        codes = self._extract_ts_const(ts_path, "ONBOARDING_ERROR_CODES")
        router_source = Path(onboarding_mod.__file__).read_text()
        for code_key in codes:
            assert code_key in router_source, (
                f"Error code {code_key} not used in router"
            )


class TestOnboardingModels:
    """[1.6-UNIT-011..015] Agent and Script model field validation"""

    def test_agent_model_fields(self):
        from models.agent import Agent

        agent = Agent.model_validate(
            {
                "name": "Test Agent",
                "voiceId": "avery",
                "businessGoal": "Lead gen",
                "safetyLevel": "strict",
            }
        )
        assert agent.name == "Test Agent"
        assert agent.voice_id == "avery"
        assert agent.business_goal == "Lead gen"
        assert agent.safety_level == "strict"
        assert agent.onboarding_complete is False
        assert agent.integration_type is None

    def test_script_model_fields(self):
        from models.script import Script

        script = Script.model_validate(
            {
                "agentId": 1,
                "name": "Initial Script",
                "content": "",
                "version": 1,
                "scriptContext": "Test context that is long enough",
            }
        )
        assert script.agent_id == 1
        assert script.name == "Initial Script"
        assert script.content == ""
        assert script.version == 1
        assert script.script_context == "Test context that is long enough"

    def test_agent_default_values(self):
        from models.agent import Agent

        agent = Agent()
        assert agent.name == "My First Agent"
        assert agent.voice_id == ""
        assert agent.safety_level == "strict"
        assert agent.onboarding_complete is False

    def test_script_default_values(self):
        from models.script import Script

        script = Script()
        assert script.name == "Initial Script"
        assert script.content == ""
        assert script.version == 1
        assert script.script_context == ""
        assert script.agent_id is None

    def test_agent_extends_tenant_model(self):
        from models.agent import Agent
        from models.base import TenantModel

        assert issubclass(Agent, TenantModel)

    def test_script_extends_tenant_model(self):
        from models.script import Script
        from models.base import TenantModel

        assert issubclass(Script, TenantModel)
