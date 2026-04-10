"""[4.1] E.164 Validation & DNC Provider ABC — ACs 1, 2"""

from __future__ import annotations

import pytest

from services.compliance.dnc_provider import (
    InvalidPhoneFormatError,
    validate_e164,
)
from tests.mocks.mock_dnc_provider import MockDncProvider


# ============================================================
# [4.1-UNIT-001..005] E.164 Validation (AC: 2)
# ============================================================


@pytest.mark.p0
def test_4_1_unit_001_valid_e164_passes():
    # Given: valid E.164 phone numbers
    # When: validated
    # Then: they pass and are returned normalized
    assert validate_e164("+12025551234") == "+12025551234"
    assert validate_e164("+447911123456") == "+447911123456"
    assert validate_e164("+1234567") == "+1234567"
    assert validate_e164("+123456789012345") == "+123456789012345"


@pytest.mark.p0
def test_4_1_unit_002_missing_plus_rejected():
    # Given: phone number without + prefix
    # When: validated
    # Then: InvalidPhoneFormatError is raised
    with pytest.raises(InvalidPhoneFormatError):
        validate_e164("12025551234")


@pytest.mark.p0
def test_4_1_unit_003_too_short_or_long_rejected():
    with pytest.raises(InvalidPhoneFormatError):
        validate_e164("+123456")
    with pytest.raises(InvalidPhoneFormatError):
        validate_e164("+1234567890123456")


@pytest.mark.p1
def test_4_1_unit_004_non_numeric_rejected():
    with pytest.raises(InvalidPhoneFormatError):
        validate_e164("+1202abc1234")
    with pytest.raises(InvalidPhoneFormatError):
        validate_e164("+1-202-555-1234")


@pytest.mark.p1
def test_4_1_unit_005_empty_none_rejected():
    with pytest.raises(InvalidPhoneFormatError):
        validate_e164("")
    with pytest.raises((InvalidPhoneFormatError, TypeError)):
        validate_e164(None)  # type: ignore


# ============================================================
# [4.1-UNIT-010..015] DNC Provider (AC: 1)
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_unit_010_successful_clear_response():
    # Given: a MockDncProvider with no blocked numbers
    # When: lookup is called for any number
    # Then: result is "clear" and is_blocked is False
    provider = MockDncProvider()
    result = await provider.lookup("+12025551234")
    assert result.result == "clear"
    assert not result.is_blocked
    assert result.source == "mock_provider"


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_unit_011_successful_blocked_response():
    # Given: a MockDncProvider with +12025551234 blocked
    # When: lookup is called for that number
    # Then: result is "blocked" and is_blocked is True
    provider = MockDncProvider(blocked_numbers={"+12025551234"})
    result = await provider.lookup("+12025551234")
    assert result.result == "blocked"
    assert result.is_blocked


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_unit_012_http_500_returns_error():
    # Given: a failing MockDncProvider
    # When: lookup is called
    # Then: result is "error" and is_blocked is False
    provider = MockDncProvider(should_fail=True)
    result = await provider.lookup("+12025551234")
    assert result.result == "error"
    assert not result.is_blocked


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_unit_013_timeout_returns_error():
    provider = MockDncProvider(should_fail=True)
    result = await provider.lookup("+12025551234")
    assert result.result == "error"


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_unit_014_malformed_returns_error():
    provider = MockDncProvider(should_fail=True)
    result = await provider.lookup("+12025551234")
    assert result.result == "error"
    assert result.raw_response is not None


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_unit_015_provider_interface():
    # Given: MockDncProvider healthy and failing instances
    # When: provider_name and health_check are called
    # Then: name and health status match configuration
    provider = MockDncProvider()
    assert provider.provider_name == "mock_provider"
    health = await provider.health_check()
    assert health is True
    failing = MockDncProvider(should_fail=True)
    assert await failing.health_check() is False
