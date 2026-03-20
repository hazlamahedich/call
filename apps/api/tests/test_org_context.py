"""
Story 1-2: Multi-layer Hierarchy & Clerk Auth Integration
API Unit Tests for Organization Context Dependencies

Test ID Format: 1.2-API-XXX
Priority: P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)
"""

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from unittest.mock import MagicMock

from dependencies.org_context import (
    get_current_org_id,
    get_current_user_id,
    get_optional_org_id,
    get_optional_user_id,
    AUTH_ERROR_CODES,
)

ORG_IDS = {
    "VALID": "org_123",
    "ALT_VALID": "org_abc",
    "MISSING": None,
}

USER_IDS = {
    "VALID": "user_456",
    "ALT_VALID": "user_xyz",
    "MISSING": None,
}


def make_mock_request(org_id=None, user_id=None):
    request = MagicMock(spec=Request)
    request.state = MagicMock()
    request.state.org_id = org_id
    request.state.user_id = user_id
    return request


class TestGetCurrentOrgId:
    """[P0] Tests for get_current_org_id dependency - AC4"""

    @pytest.mark.asyncio
    async def test_1_2_api_001_returns_org_id_when_present(self):
        request = make_mock_request(org_id=ORG_IDS["VALID"])
        result = await get_current_org_id(request)
        assert result == ORG_IDS["VALID"]

    @pytest.mark.asyncio
    async def test_1_2_api_002_raises_403_when_org_id_missing(self):
        request = make_mock_request(org_id=ORG_IDS["MISSING"])
        with pytest.raises(HTTPException) as exc_info:
            await get_current_org_id(request)
        exc = exc_info.value
        assert exc.status_code == 403
        assert exc.detail["code"] == AUTH_ERROR_CODES["AUTH_FORBIDDEN"]
        assert "Organization context required" in exc.detail["message"]


class TestGetCurrentUserId:
    """[P0] Tests for get_current_user_id dependency - AC4"""

    @pytest.mark.asyncio
    async def test_1_2_api_003_returns_user_id_when_present(self):
        request = make_mock_request(user_id=USER_IDS["VALID"])
        result = await get_current_user_id(request)
        assert result == USER_IDS["VALID"]

    @pytest.mark.asyncio
    async def test_1_2_api_004_raises_403_when_user_id_missing(self):
        request = make_mock_request(user_id=USER_IDS["MISSING"])
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(request)
        exc = exc_info.value
        assert exc.status_code == 403
        assert exc.detail["code"] == AUTH_ERROR_CODES["AUTH_FORBIDDEN"]
        assert "User authentication required" in exc.detail["message"]


class TestGetOptionalOrgId:
    """[P1] Tests for get_optional_org_id dependency - AC4"""

    @pytest.mark.asyncio
    async def test_1_2_api_005_returns_org_id_when_present(self):
        request = make_mock_request(org_id=ORG_IDS["ALT_VALID"])
        result = await get_optional_org_id(request)
        assert result == ORG_IDS["ALT_VALID"]

    @pytest.mark.asyncio
    async def test_1_2_api_006_returns_none_when_org_id_missing(self):
        request = make_mock_request(org_id=ORG_IDS["MISSING"])
        result = await get_optional_org_id(request)
        assert result is None


class TestGetOptionalUserId:
    """[P1] Tests for get_optional_user_id dependency - AC4"""

    @pytest.mark.asyncio
    async def test_1_2_api_007_returns_user_id_when_present(self):
        request = make_mock_request(user_id=USER_IDS["ALT_VALID"])
        result = await get_optional_user_id(request)
        assert result == USER_IDS["ALT_VALID"]

    @pytest.mark.asyncio
    async def test_1_2_api_008_returns_none_when_user_id_missing(self):
        request = make_mock_request(user_id=USER_IDS["MISSING"])
        result = await get_optional_user_id(request)
        assert result is None


class TestAuthErrorCodes:
    """[P1] Tests for AUTH_ERROR_CODES constant verification - AC4"""

    def test_1_2_api_009_error_codes_are_defined(self):
        assert AUTH_ERROR_CODES["AUTH_INVALID_TOKEN"] == "AUTH_INVALID_TOKEN"
        assert AUTH_ERROR_CODES["AUTH_TOKEN_EXPIRED"] == "AUTH_TOKEN_EXPIRED"
        assert AUTH_ERROR_CODES["AUTH_UNAUTHORIZED"] == "AUTH_UNAUTHORIZED"
        assert AUTH_ERROR_CODES["AUTH_FORBIDDEN"] == "AUTH_FORBIDDEN"
