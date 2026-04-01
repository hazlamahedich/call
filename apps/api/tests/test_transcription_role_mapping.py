"""
Story 2.2: Real-time Audio Stream & Transcription Pipeline
Role Mapping Unit Tests

Test ID Format: [2.2-UNIT-XXX]
"""

import pytest

from services.transcription import _map_role


class TestMapRole:
    """[2.2-UNIT-001..004] Role mapping tests"""

    def test_2_2_unit_001_P2_given_assistant_role_when_map_then_returns_assistant_ai(
        self,
    ):
        assert _map_role("assistant") == "assistant-ai"

    def test_2_2_unit_002_P2_given_user_role_when_map_then_returns_lead(self):
        assert _map_role("user") == "lead"

    def test_2_2_unit_003_P2_given_human_role_when_map_then_returns_assistant_human(
        self,
    ):
        assert _map_role("human") == "assistant-human"

    def test_2_2_unit_004_P2_given_unknown_role_when_map_then_returns_lead(self):
        assert _map_role("unknown") == "lead"


class TestMapRoleExtended:
    """[2.2-UNIT-042] Extended role mapping"""

    def test_2_2_unit_042_P2_given_ai_role_when_map_then_returns_assistant_ai(self):
        assert _map_role("ai") == "assistant-ai"
