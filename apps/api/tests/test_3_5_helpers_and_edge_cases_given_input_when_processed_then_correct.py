"""Story 3.5: Helper Functions & Edge Cases.

Tests for _ensure_dict, _ensure_list, null expiry in _check_session_expiry,
and session creation with lead_id.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from conftest_3_5 import (
    TEST_ORG,
    mock_session,
    lab_service,
)
from services.script_lab import ScriptLabService, _ensure_dict, _ensure_list


class TestEnsureDict:
    @pytest.mark.p0
    def test_3_5_110_given_valid_json_string_when_ensure_dict_then_parsed(self):
        result = _ensure_dict('{"key": "value"}')
        assert result == {"key": "value"}

    @pytest.mark.p0
    def test_3_5_111_given_dict_input_when_ensure_dict_then_returned_as_is(self):
        result = _ensure_dict({"a": 1})
        assert result == {"a": 1}

    @pytest.mark.p1
    def test_3_5_112_given_invalid_json_string_when_ensure_dict_then_empty_dict(self):
        result = _ensure_dict("not json{")
        assert result == {}

    @pytest.mark.p1
    def test_3_5_113_given_none_when_ensure_dict_then_empty_dict(self):
        result = _ensure_dict(None)
        assert result == {}

    @pytest.mark.p1
    def test_3_5_114_given_integer_when_ensure_dict_then_empty_dict(self):
        result = _ensure_dict(42)
        assert result == {}


class TestEnsureList:
    @pytest.mark.p0
    def test_3_5_115_given_valid_json_array_string_when_ensure_list_then_parsed(self):
        result = _ensure_list("[1, 2, 3]")
        assert result == [1, 2, 3]

    @pytest.mark.p0
    def test_3_5_116_given_list_input_when_ensure_list_then_returned_as_is(self):
        result = _ensure_list([1, 2])
        assert result == [1, 2]

    @pytest.mark.p1
    def test_3_5_117_given_invalid_json_string_when_ensure_list_then_empty_list(self):
        result = _ensure_list("not json[")
        assert result == []

    @pytest.mark.p1
    def test_3_5_118_given_none_when_ensure_list_then_empty_list(self):
        result = _ensure_list(None)
        assert result == []

    @pytest.mark.p1
    def test_3_5_119_given_integer_when_ensure_list_then_empty_list(self):
        result = _ensure_list(42)
        assert result == []


@pytest.mark.asyncio
class TestCheckSessionExpiryEdgeCases:
    @pytest.mark.p0
    async def test_3_5_120_given_null_expires_at_when_checked_then_500(
        self, mock_session, lab_service
    ):
        row = (
            1,
            TEST_ORG,
            1,
            1,
            None,
            None,
            None,
            "active",
            0,
        )

        with pytest.raises(HTTPException) as exc_info:
            await lab_service._check_session_expiry(row)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error"]["code"] == "invalid_session"

    @pytest.mark.p1
    async def test_3_5_121_given_naive_datetime_expires_at_when_checked_then_tz_added(
        self, mock_session, lab_service
    ):
        future_naive = datetime.now(timezone.utc) + timedelta(hours=1)
        future_naive = future_naive.replace(tzinfo=None)

        row = (
            1,
            TEST_ORG,
            1,
            1,
            None,
            None,
            future_naive,
            "active",
            0,
        )

        mock_session.execute = AsyncMock(return_value=MagicMock())
        mock_session.flush = AsyncMock()

        await lab_service._check_session_expiry(row)

        mock_session.execute.assert_not_awaited()


@pytest.mark.asyncio
class TestCreateSessionWithLead:
    @pytest.mark.p1
    async def test_3_5_122_given_lead_id_when_creating_session_then_lead_loaded(
        self, mock_session, lab_service
    ):
        with (
            patch("services.script_lab.load_agent_for_context", new_callable=AsyncMock),
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ),
            patch(
                "services.script_lab.load_lead_for_context", new_callable=AsyncMock
            ) as mock_load_lead,
        ):

            def assign_id(instance):
                instance.id = 1

            mock_session.add = MagicMock(side_effect=assign_id)
            mock_session.flush = AsyncMock()

            with patch("services.script_lab.settings") as mock_settings:
                mock_settings.SCRIPT_LAB_SESSION_TTL_SECONDS = 3600
                await lab_service.create_session(
                    org_id=TEST_ORG, agent_id=1, script_id=2, lead_id=5
                )

        mock_load_lead.assert_awaited_once_with(mock_session, 5, TEST_ORG)
