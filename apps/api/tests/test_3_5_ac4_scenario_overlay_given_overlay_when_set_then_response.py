"""Story 3.5 AC4: Scenario Overlay (set_scenario_overlay).

Tests for ownership verification, expiry enforcement, value sanitization
wiring, and response assembly in set_scenario_overlay.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest_3_5 import (
    TEST_ORG,
    TEST_ORG_B,
    mock_session,
    lab_service,
    make_overlay_row,
)
from services.script_lab import ScriptLabService


@pytest.mark.asyncio
class TestAC4ScenarioOverlay:
    @pytest.mark.p0
    async def test_3_5_070_given_active_session_when_overlay_set_then_response_returned(
        self, mock_session, lab_service
    ):
        active_row = make_overlay_row()
        updated_row = make_overlay_row(scenario_overlay={"name": "Acme"})

        call_count = 0

        async def mock_execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.fetchone.return_value = active_row
            elif call_count == 2:
                pass
            elif call_count == 3:
                result.fetchone.return_value = updated_row
            return result

        mock_session.execute = AsyncMock(side_effect=mock_execute)
        mock_session.flush = AsyncMock()

        with patch(
            "services.variable_injection.VariableInjectionService._sanitize_value",
            side_effect=lambda v: v,
        ):
            result = await lab_service.set_scenario_overlay(
                org_id=TEST_ORG,
                session_id=1,
                overlay={"name": "Acme"},
            )

        assert result.session_id == 1
        assert result.scenario_overlay == {"name": "Acme"}

    @pytest.mark.p0
    async def test_3_5_071_given_nonexistent_session_when_overlay_then_404(
        self, mock_session, lab_service
    ):
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await lab_service.set_scenario_overlay(
                org_id=TEST_ORG, session_id=999, overlay={"k": "v"}
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"]["code"] == "session_not_found"

    @pytest.mark.p0
    async def test_3_5_072_given_cross_tenant_session_when_overlay_then_403(
        self, mock_session, lab_service
    ):
        mock_result = MagicMock()
        mock_result.fetchone.return_value = make_overlay_row(org_id=TEST_ORG_B)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await lab_service.set_scenario_overlay(
                org_id=TEST_ORG, session_id=1, overlay={"k": "v"}
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"]["code"] == "NAMESPACE_VIOLATION"

    @pytest.mark.p0
    async def test_3_5_073_given_expired_session_when_overlay_then_410(
        self, mock_session, lab_service
    ):
        mock_result = MagicMock()
        mock_result.fetchone.return_value = make_overlay_row(status="expired")
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await lab_service.set_scenario_overlay(
                org_id=TEST_ORG, session_id=1, overlay={"k": "v"}
            )

        assert exc_info.value.status_code == 410
        assert exc_info.value.detail["error"]["code"] == "session_expired"

    @pytest.mark.p1
    async def test_3_5_074_given_session_past_ttl_but_active_status_when_overlay_then_410(
        self, mock_session, lab_service
    ):
        mock_result = MagicMock()
        mock_result.fetchone.return_value = make_overlay_row(
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await lab_service.set_scenario_overlay(
                org_id=TEST_ORG, session_id=1, overlay={"k": "v"}
            )

        assert exc_info.value.status_code == 410

    @pytest.mark.p1
    async def test_3_5_075_given_overlay_values_when_sanitized_then_each_value_processed(
        self, mock_session, lab_service
    ):
        active_row = make_overlay_row()
        updated_row = make_overlay_row(scenario_overlay={"a": "safe_a", "b": "safe_b"})

        call_count = 0

        async def mock_execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.fetchone.return_value = active_row
            elif call_count == 3:
                result.fetchone.return_value = updated_row
            return result

        mock_session.execute = AsyncMock(side_effect=mock_execute)
        mock_session.flush = AsyncMock()

        sanitized_values = []

        def fake_sanitize(v):
            sanitized_values.append(v)
            return f"safe_{v}"

        with patch(
            "services.variable_injection.VariableInjectionService._sanitize_value",
            side_effect=fake_sanitize,
        ):
            await lab_service.set_scenario_overlay(
                org_id=TEST_ORG,
                session_id=1,
                overlay={"a": "val_a", "b": "val_b"},
            )

        assert sanitized_values == ["val_a", "val_b"]

    @pytest.mark.p1
    async def test_3_5_076_given_naive_expires_at_when_overlay_then_tz_added_and_checked(
        self, mock_session, lab_service
    ):
        naive_past = datetime.now(timezone.utc) - timedelta(minutes=5)
        naive_past = naive_past.replace(tzinfo=None)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = make_overlay_row(expires_at=naive_past)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await lab_service.set_scenario_overlay(
                org_id=TEST_ORG, session_id=1, overlay={"k": "v"}
            )

        assert exc_info.value.status_code == 410

    @pytest.mark.p1
    async def test_3_5_077_given_session_vanished_after_update_when_overlay_then_404(
        self, mock_session, lab_service
    ):
        active_row = make_overlay_row()

        call_count = 0

        async def mock_execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.fetchone.return_value = active_row
            elif call_count == 2:
                pass
            elif call_count == 3:
                result.fetchone.return_value = None
            return result

        mock_session.execute = AsyncMock(side_effect=mock_execute)
        mock_session.flush = AsyncMock()

        with (
            patch(
                "services.variable_injection.VariableInjectionService._sanitize_value",
                side_effect=lambda v: v,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await lab_service.set_scenario_overlay(
                org_id=TEST_ORG, session_id=1, overlay={"k": "v"}
            )

        assert exc_info.value.status_code == 404
        assert "not found after update" in exc_info.value.detail["error"]["message"]
