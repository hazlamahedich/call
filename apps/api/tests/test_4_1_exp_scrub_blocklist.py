"""[4.1-EXP] scrub_leads_batch expanded + blocklist CRUD + error messages"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.compliance.dnc_provider import DncCheckResult
from services.compliance.exceptions import ComplianceBlockError
from helpers.dnc_helpers import make_mock_session


# ============================================================
# [4.1-EXP-UNIT] scrub_leads_batch — expanded
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_exp_scrub_mixed_blocked_and_clear():
    # Given: 3 leads, one blocked
    # When: scrub_leads_batch runs
    # Then: summary shows 3 total, 1 blocked
    mock_session = make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (1, "+12025551234"),
        (2, "+12025559999"),
        (3, "+12025550000"),
    ]
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def fake_check(session, phone, org_id, redis, **kw):
        is_blocked = phone == "+12025559999"
        return DncCheckResult(
            phone_number=phone,
            is_blocked=is_blocked,
            source="national_dnc" if is_blocked else "mock",
            result="blocked" if is_blocked else "clear",
        )

    with (
        patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check),
        patch("services.compliance.dnc.add_to_blocklist", new_callable=AsyncMock),
    ):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1, 2, 3], None)
    assert summary.total == 3
    assert summary.blocked == 1


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_scrub_dedup_phones():
    # Given: 2 leads with same phone
    # When: scrub_leads_batch runs
    # Then: DNC check is called only once, 1 skipped
    mock_session = make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1, "+12025551234"), (2, "+12025551234")]
    mock_session.execute = AsyncMock(return_value=mock_result)

    check_count = 0

    async def fake_check(session, phone, org_id, redis, **kw):
        nonlocal check_count
        check_count += 1
        return DncCheckResult(phone_number=phone, result="clear", source="mock")

    with patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1, 2], None)
    assert check_count == 1
    assert summary.skipped == 1


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_scrub_error_marks_unchecked():
    mock_session = make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1, "+12025551234")]
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def fake_check(session, phone, org_id, redis, **kw):
        return DncCheckResult(
            phone_number=phone, result="error", source="mock_provider"
        )

    with patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1], None)
    assert summary.unchecked == 1


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_scrub_compliance_error_caught():
    mock_session = make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1, "+12025551234")]
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def fake_check(session, phone, org_id, redis, **kw):
        raise ComplianceBlockError(
            code="DNC_BLOCKED", phone_number=phone, source="national_dnc"
        )

    with patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1], None)
    assert summary.unchecked == 1


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_scrub_unexpected_exception_caught():
    mock_session = make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1, "+12025551234")]
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def fake_check(session, phone, org_id, redis, **kw):
        raise RuntimeError("unexpected")

    with patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1], None)
    assert summary.unchecked == 1


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_scrub_blocklist_failure_tolerated():
    mock_session = make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1, "+12025559999")]
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def fake_check(session, phone, org_id, redis, **kw):
        return DncCheckResult(
            phone_number=phone, is_blocked=True, source="national_dnc", result="blocked"
        )

    with (
        patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check),
        patch(
            "services.compliance.dnc.add_to_blocklist",
            new_callable=AsyncMock,
            side_effect=Exception("db error"),
        ),
    ):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1], None)
    assert summary.blocked == 1


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_scrub_empty_list():
    mock_session = make_mock_session()
    from services.compliance.dnc import scrub_leads_batch

    summary = await scrub_leads_batch(mock_session, "org1", [], None)
    assert summary.total == 0
    assert summary.blocked == 0
    assert summary.unchecked == 0


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_scrub_null_phone_skipped():
    mock_session = make_mock_session()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1, None), (2, "+12025551234")]
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def fake_check(session, phone, org_id, redis, **kw):
        return DncCheckResult(phone_number=phone, result="clear", source="mock")

    with patch("services.compliance.dnc.check_dnc_realtime", side_effect=fake_check):
        from services.compliance.dnc import scrub_leads_batch

        summary = await scrub_leads_batch(mock_session, "org1", [1, 2], None)
    assert summary.total == 2


# ============================================================
# [4.1-EXP-UNIT] blocklist CRUD
# ============================================================


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_exp_blocklist_remove_success():
    from services.compliance.blocklist import remove_from_blocklist

    mock_session = make_mock_session()
    mock_session.execute = AsyncMock(return_value=MagicMock(rowcount=1))

    with patch(
        "services.compliance.blocklist.set_tenant_context", new_callable=AsyncMock
    ):
        removed = await remove_from_blocklist(mock_session, "org1", "+12025551234")
    assert removed is True


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_blocklist_remove_not_found():
    from services.compliance.blocklist import remove_from_blocklist

    mock_session = make_mock_session()
    mock_session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

    with patch(
        "services.compliance.blocklist.set_tenant_context", new_callable=AsyncMock
    ):
        removed = await remove_from_blocklist(mock_session, "org1", "+12025551234")
    assert removed is False


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_exp_blocklist_add_success():
    from services.compliance.blocklist import add_to_blocklist

    mock_session = make_mock_session()
    mock_result = MagicMock()
    mock_result.first.return_value = (
        1,
        "org1",
        "+12025551234",
        "national_dnc",
        "test",
        42,
        datetime.now(timezone.utc),
        None,
        datetime.now(timezone.utc),
        datetime.now(timezone.utc),
        False,
    )
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch(
        "services.compliance.blocklist.set_tenant_context", new_callable=AsyncMock
    ):
        entry = await add_to_blocklist(
            mock_session, "org1", "+12025551234", "national_dnc", reason="test"
        )
    assert entry.phone_number == "+12025551234"
    assert entry.source == "national_dnc"


@pytest.mark.asyncio
@pytest.mark.p2
async def test_4_1_exp_blocklist_add_no_row_raises():
    from services.compliance.blocklist import add_to_blocklist

    mock_session = make_mock_session()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    with (
        patch(
            "services.compliance.blocklist.set_tenant_context", new_callable=AsyncMock
        ),
        pytest.raises(RuntimeError, match="blocklist upsert returned no row"),
    ):
        await add_to_blocklist(mock_session, "org1", "+12025551234", "national_dnc")


@pytest.mark.asyncio
@pytest.mark.p1
async def test_4_1_exp_blocklist_check_no_match():
    from services.compliance.blocklist import check_tenant_blocklist

    mock_session = make_mock_session()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch(
        "services.compliance.blocklist.set_tenant_context", new_callable=AsyncMock
    ):
        result = await check_tenant_blocklist(mock_session, "+12025551234", "org1")
    assert result is None


# ============================================================
# [4.1-EXP-UNIT] ComplianceBlockError — message format
# ============================================================


@pytest.mark.p3
def test_4_1_exp_compliance_error_message_with_call_id():
    err = ComplianceBlockError(
        code="DNC_BLOCKED",
        phone_number="+12025551234",
        call_id=99,
        source="national_dnc",
        retry_after_seconds=30,
    )
    msg = str(err)
    assert "DNC_BLOCKED" in msg
    assert "call_id=99" in msg
    assert "retry after 30s" in msg


@pytest.mark.p3
def test_4_1_exp_compliance_error_message_minimal():
    err = ComplianceBlockError(code="DNC_BLOCKED", phone_number="+12025551234")
    msg = str(err)
    assert "DNC_BLOCKED" in msg
    assert "call_id" not in msg
    assert "retry" not in msg
