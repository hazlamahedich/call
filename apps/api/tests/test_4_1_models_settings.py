"""[4.1] Models, Settings, Errors, Integration — ACs 3, 6, 7, 9, 10, 12"""

from __future__ import annotations

import pytest

from services.compliance.dnc_provider import DncScrubSummary
from services.compliance.exceptions import ComplianceBlockError


# ============================================================
# [4.1-UNIT-050..053] Model tests (ACs: 6, 7, 9)
# ============================================================


@pytest.mark.p1
def test_4_1_unit_052_call_model_accepts_compliance_fields():
    # Given: Call model with compliance fields
    # When: model_validate is called with full data
    # Then: all compliance fields are populated correctly
    from models.call import Call

    call = Call.model_validate(
        {
            "phoneNumber": "+12025551234",
            "status": "pending",
            "complianceStatus": "passed",
            "stateCode": "FL",
            "consentCaptured": True,
            "gracefulGoodnightTriggered": False,
        }
    )
    assert call.compliance_status == "passed"
    assert call.state_code == "FL"
    assert call.consent_captured is True
    assert call.graceful_goodnight_triggered is False


@pytest.mark.p1
def test_4_1_unit_053_legacy_null_compliance_status():
    # Given: Call model with no compliance fields
    # When: model_validate is called with legacy data
    # Then: compliance fields default to None/False
    from models.call import Call

    call = Call.model_validate({"phoneNumber": "+12025551234", "status": "completed"})
    assert call.compliance_status is None
    assert call.consent_captured is False


@pytest.mark.p1
def test_4_1_unit_050_dnc_check_log_model():
    from models.dnc_check_log import DncCheckLog

    log = DncCheckLog.model_validate(
        {
            "phoneNumber": "+12025551234",
            "checkType": "pre_dial",
            "source": "national_dnc",
            "result": "clear",
            "responseTimeMs": 45,
        }
    )
    assert log.phone_number == "+12025551234"
    assert log.check_type == "pre_dial"
    assert log.result == "clear"
    assert log.response_time_ms == 45


@pytest.mark.p1
def test_4_1_unit_051_blocklist_entry_model():
    from models.blocklist_entry import BlocklistEntry

    entry = BlocklistEntry.model_validate(
        {
            "phoneNumber": "+12025551234",
            "source": "national_dnc",
            "reason": "On National DNC list",
        }
    )
    assert entry.phone_number == "+12025551234"
    assert entry.source == "national_dnc"


# ============================================================
# [4.1-INT-004] _compliance_pre_check fully removed (AC: 10)
# ============================================================


@pytest.mark.p1
def test_4_1_int_004_compliance_pre_check_removed():
    import routers.calls as calls_module

    assert not hasattr(calls_module, "_compliance_pre_check")


# ============================================================
# Settings tests (AC: 12)
# ============================================================


@pytest.mark.p2
def test_4_1_settings_dnc_defaults():
    from config.settings import Settings

    s = Settings()
    assert s.DNC_API_KEY == ""
    assert s.DNC_CACHE_BLOCKED_TTL_SECONDS == 259200
    assert s.DNC_CACHE_CLEAR_TTL_SECONDS == 14400
    assert s.DNC_BATCH_SIZE == 1000
    assert s.DNC_PRE_DIAL_TIMEOUT_MS == 100
    assert s.DNC_CIRCUIT_BREAKER_THRESHOLD == 5
    assert s.DNC_CIRCUIT_OPEN_SEC == 30
    assert s.DNC_FAIL_CLOSED_ENABLED is True


# ============================================================
# ComplianceBlockError tests (AC: 10)
# ============================================================


@pytest.mark.p1
def test_4_1_compliance_block_error():
    err = ComplianceBlockError(
        code="DNC_BLOCKED",
        phone_number="+12025551234",
        call_id=42,
        source="national_dnc",
        retry_after_seconds=60,
    )
    assert err.code == "DNC_BLOCKED"
    assert err.call_id == 42
    assert err.phone_number == "+12025551234"
    assert err.source == "national_dnc"
    assert "DNC_BLOCKED" in str(err)


@pytest.mark.p2
def test_4_1_compliance_block_error_invalid_format():
    err = ComplianceBlockError(
        code="DNC_INVALID_PHONE_FORMAT",
        phone_number="not-a-number",
        source="validation",
    )
    assert err.code == "DNC_INVALID_PHONE_FORMAT"
    assert err.retry_after_seconds is None


# ============================================================
# DncScrubSummary tests (AC: 3)
# ============================================================


@pytest.mark.p2
def test_4_1_dnc_scrub_summary_defaults():
    summary = DncScrubSummary(total=10, blocked=3, unchecked=1)
    assert summary.total == 10
    assert summary.blocked == 3
    assert summary.unchecked == 1
    assert "national_dnc" in summary.sources
    assert "state_dnc" in summary.sources
    assert "tenant_blocklist" in summary.sources


# ============================================================
# Phone masking test (AC: 11 — PII)
# ============================================================


@pytest.mark.p2
def test_4_1_phone_masking():
    from services.compliance.dnc import _mask_phone

    assert _mask_phone("+12025551234") == "+12***34"
    assert _mask_phone("+12") == "***"
