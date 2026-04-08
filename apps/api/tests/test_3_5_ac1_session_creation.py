"""Story 3.5 AC1: Session Creation.

Tests for ScriptLab session creation with org isolation and TTL.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest_3_5 import *
from services.script_lab import ScriptLabService
from schemas.script_lab import CreateLabSessionRequest


@pytest.mark.asyncio
class TestAC1SessionCreation:
    @pytest.mark.p0
    async def test_3_5_001_given_agent_and_script_when_creating_session_then_session_id_returned(
        self, mock_session, lab_service
    ):
        # [3.5-UNIT-001]
        with (
            patch("services.script_lab.load_agent_for_context", new_callable=AsyncMock),
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ),
        ):

            def assign_id(instance):
                instance.id = 1

            mock_session.add = MagicMock(side_effect=assign_id)
            mock_session.flush = AsyncMock()

            with patch("services.script_lab.settings") as mock_settings:
                mock_settings.SCRIPT_LAB_SESSION_TTL_SECONDS = 3600
                result = await lab_service.create_session(
                    org_id=TEST_ORG, agent_id=1, script_id=2
                )

            assert result.session_id == 1
            assert result.agent_id == 1
            assert result.script_id == 2

    @pytest.mark.p0
    async def test_3_5_002_given_new_session_when_inspecting_then_org_id_matches_caller(
        self, mock_session, lab_service
    ):
        # [3.5-UNIT-002]
        captured_org = None

        with (
            patch("services.script_lab.load_agent_for_context", new_callable=AsyncMock),
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ) as mock_script,
        ):

            def capture_add(instance):
                nonlocal captured_org
                instance.id = 1
                captured_org = instance.org_id

            mock_session.add = MagicMock(side_effect=capture_add)
            mock_session.flush = AsyncMock()

            with patch("services.script_lab.settings") as mock_settings:
                mock_settings.SCRIPT_LAB_SESSION_TTL_SECONDS = 3600
                await lab_service.create_session(
                    org_id=TEST_ORG, agent_id=1, script_id=2
                )

            assert captured_org == TEST_ORG

    @pytest.mark.p0
    async def test_3_5_003_given_new_session_when_inspecting_then_expires_at_about_one_hour(
        self, mock_session, lab_service
    ):
        # [3.5-UNIT-003]
        captured_expires_at = None

        with (
            patch("services.script_lab.load_agent_for_context", new_callable=AsyncMock),
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ),
        ):

            def capture_expires(instance):
                nonlocal captured_expires_at
                instance.id = 1
                captured_expires_at = instance.expires_at

            mock_session.add = MagicMock(side_effect=capture_expires)
            mock_session.flush = AsyncMock()

            before = datetime.now(timezone.utc)
            with patch("services.script_lab.settings") as mock_settings:
                mock_settings.SCRIPT_LAB_SESSION_TTL_SECONDS = 3600
                result = await lab_service.create_session(
                    org_id=TEST_ORG, agent_id=1, script_id=2
                )
            after = datetime.now(timezone.utc)

            expected_min = before + timedelta(seconds=3600)
            expected_max = after + timedelta(seconds=3600)
            assert expected_min <= captured_expires_at <= expected_max

    @pytest.mark.p0
    async def test_3_5_004_given_creation_without_required_fields_when_validated_then_rejected(
        self,
    ):
        # [3.5-UNIT-004]
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            CreateLabSessionRequest()

        with pytest.raises(pydantic.ValidationError):
            CreateLabSessionRequest(agent_id=1)

        with pytest.raises(pydantic.ValidationError):
            CreateLabSessionRequest(script_id=1)

        valid = CreateLabSessionRequest(agent_id=1, script_id=2)
        assert valid.agent_id == 1
        assert valid.script_id == 2
