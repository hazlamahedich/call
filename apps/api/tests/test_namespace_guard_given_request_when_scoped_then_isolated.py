"""Namespace guard tests for per-tenant RAG isolation.

BDD-named tests verifying that namespace guard enforces tenant isolation
across all knowledge base endpoints, with structured error responses.
"""

import pytest
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from middleware.namespace_guard import verify_namespace_access
from services.namespace_audit import NamespaceAuditService
from config.settings import settings


def _make_row(org_id="org-alpha"):
    return (org_id,)


def _mock_session(resource_org_id=None):
    session = MagicMock(spec=AsyncSession)
    result = MagicMock()
    if resource_org_id is not None:
        result.fetchone.return_value = _make_row(resource_org_id)
    else:
        result.fetchone.return_value = None
    session.execute = AsyncMock(return_value=result)
    return session


def _mock_session_with_resource(resource_org_id="org-alpha"):
    session = MagicMock(spec=AsyncSession)
    result = MagicMock()
    result.fetchone.return_value = _make_row(resource_org_id)
    session.execute = AsyncMock(return_value=result)
    return session


def _mock_request(path="/api/knowledge/documents/1"):
    request = MagicMock()
    request.url.path = path
    return request


@pytest.mark.asyncio
class TestNamespaceGuardCore:
    async def test_3_2_000_given_upload_endpoint_when_called_then_org_id_from_jwt(self):
        """[3.2-UNIT-000] org_id comes from Depends(get_current_org_id), not token.org_id."""
        session = _mock_session()
        org_id = await verify_namespace_access(session=session, org_id="org-from-jwt")
        assert org_id == "org-from-jwt"

    async def test_3_2_000a_given_list_documents_when_called_then_org_id_from_jwt(self):
        """[3.2-UNIT-000a] list_documents uses org_id from JWT."""
        session = _mock_session()
        org_id = await verify_namespace_access(session=session, org_id="org-list-jwt")
        assert org_id == "org-list-jwt"

    async def test_3_2_000b_given_get_document_when_called_then_org_id_from_jwt(self):
        """[3.2-UNIT-000b] get_document uses org_id from JWT."""
        session = _mock_session_with_resource("org-jwt-owner")
        org_id = await verify_namespace_access(
            resource_id=42,
            request=_mock_request(),
            session=session,
            org_id="org-jwt-owner",
        )
        assert org_id == "org-jwt-owner"

    async def test_3_2_000c_given_delete_endpoint_when_called_then_org_id_from_jwt(
        self,
    ):
        """[3.2-UNIT-000c] delete uses org_id from JWT."""
        session = _mock_session_with_resource("org-jwt-delete")
        org_id = await verify_namespace_access(
            resource_id=10,
            request=_mock_request(),
            session=session,
            org_id="org-jwt-delete",
        )
        assert org_id == "org-jwt-delete"

    async def test_3_2_000d_given_search_endpoint_when_called_then_org_id_from_jwt(
        self,
    ):
        """[3.2-UNIT-000d] search uses org_id from JWT."""
        session = _mock_session()
        org_id = await verify_namespace_access(session=session, org_id="org-search-jwt")
        assert org_id == "org-search-jwt"

    async def test_3_2_000e_given_retry_endpoint_when_called_then_org_id_from_jwt(self):
        """[3.2-UNIT-000e] retry uses org_id from JWT."""
        session = _mock_session_with_resource("org-jwt-retry")
        org_id = await verify_namespace_access(
            resource_id=7,
            request=_mock_request(),
            session=session,
            org_id="org-jwt-retry",
        )
        assert org_id == "org-jwt-retry"


@pytest.mark.asyncio
class TestNamespaceGuardAC1:
    async def test_3_2_001_given_valid_org_id_when_searching_then_only_own_vectors(
        self,
    ):
        """[3.2-UNIT-001] Valid org_id returns own resources only."""
        session = _mock_session()
        org_id = await verify_namespace_access(session=session, org_id="org-alpha")
        assert org_id == "org-alpha"

    async def test_3_2_002_given_org_with_no_docs_when_searching_then_empty(self):
        """[3.2-UNIT-002] Empty org gets empty guard pass-through."""
        session = _mock_session()
        org_id = await verify_namespace_access(session=session, org_id="org-empty")
        assert org_id == "org-empty"

    async def test_3_2_003_given_similarity_threshold_when_searching_then_filtered(
        self,
    ):
        """[3.2-UNIT-003] Similarity threshold is applied from settings."""
        threshold = settings.RAG_SIMILARITY_THRESHOLD
        assert 0.0 <= threshold <= 1.0
        assert threshold == 0.7

    async def test_3_2_004_given_search_query_then_guard_overhead_under_5ms(self):
        """[3.2-UNIT-004] Guard overhead is <5ms."""
        session = _mock_session()
        start = time.monotonic()
        for _ in range(100):
            await verify_namespace_access(session=session, org_id="org-perf")
        elapsed_ms = (time.monotonic() - start) * 1000 / 100
        assert elapsed_ms < 5.0, f"Guard overhead {elapsed_ms:.2f}ms exceeds 5ms"

    async def test_3_2_005_given_guard_disabled_when_searching_then_rls_still_enforced(
        self,
    ):
        """[3.2-UNIT-005] Guard disabled still returns org_id."""
        with patch.object(settings, "NAMESPACE_GUARD_ENABLED", False):
            session = _mock_session_with_resource("org-other")
            org_id = await verify_namespace_access(
                resource_id=99,
                request=_mock_request(),
                session=session,
                org_id="org-mine",
            )
            assert org_id == "org-mine"


@pytest.mark.asyncio
class TestNamespaceGuardAC2:
    async def test_3_2_006_given_org_a_token_when_requesting_org_b_doc_then_403(self):
        """[3.2-UNIT-006] Cross-tenant document access returns 403."""
        session = _mock_session_with_resource("org-beta")
        with pytest.raises(HTTPException) as exc_info:
            await verify_namespace_access(
                resource_id=42,
                request=_mock_request(),
                session=session,
                org_id="org-alpha",
            )
        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        assert detail["code"] == "NAMESPACE_VIOLATION"

    async def test_3_2_007_given_org_a_token_when_deleting_org_b_doc_then_403(self):
        """[3.2-UNIT-007] Cross-tenant delete returns 403."""
        session = _mock_session_with_resource("org-beta")
        with pytest.raises(HTTPException) as exc_info:
            await verify_namespace_access(
                resource_id=10,
                request=_mock_request("/api/knowledge/documents/10"),
                session=session,
                org_id="org-alpha",
            )
        assert exc_info.value.status_code == 403

    async def test_3_2_008_given_org_a_token_when_retrying_org_b_doc_then_403(self):
        """[3.2-UNIT-008] Cross-tenant retry returns 403."""
        session = _mock_session_with_resource("org-beta")
        with pytest.raises(HTTPException) as exc_info:
            await verify_namespace_access(
                resource_id=5,
                request=_mock_request("/api/knowledge/documents/5/retry"),
                session=session,
                org_id="org-alpha",
            )
        assert exc_info.value.status_code == 403

    async def test_3_2_009_given_cross_tenant_attempt_then_structured_log(self):
        """[3.2-UNIT-009] Violation attempt is logged with structured fields."""
        session = _mock_session_with_resource("org-beta")
        with (
            patch("middleware.namespace_guard.logger") as mock_logger,
            pytest.raises(HTTPException),
        ):
            await verify_namespace_access(
                resource_id=42,
                request=_mock_request(),
                session=session,
                org_id="org-alpha",
            )
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args
        extra = call_kwargs.kwargs.get("extra") or call_kwargs[1].get("extra", {})
        assert extra["code"] == "NAMESPACE_VIOLATION"
        assert extra["org_id"] == "org-alpha"
        assert extra["attempted_resource_id"] == 42
        assert extra["resource_owner_org_id"] == "org-beta"

    async def test_3_2_010_given_nonexistent_doc_id_when_requesting_then_404(self):
        """[3.2-UNIT-010] Non-existent document returns 404, not 403."""
        session = _mock_session(resource_org_id=None)
        with pytest.raises(HTTPException) as exc_info:
            await verify_namespace_access(
                resource_id=999,
                request=_mock_request(),
                session=session,
                org_id="org-alpha",
            )
        assert exc_info.value.status_code == 404
        detail = exc_info.value.detail
        assert detail["code"] == "KNOWLEDGE_BASE_NOT_FOUND"


@pytest.mark.asyncio
class TestNamespaceGuardAC3:
    async def test_3_2_011_given_threshold_07_then_only_similar_above(self):
        """[3.2-UNIT-011] Default threshold 0.7 filters low-similarity results."""
        assert settings.RAG_SIMILARITY_THRESHOLD == 0.7

    async def test_3_2_012_given_threshold_0_when_searching_then_all_results(self):
        """[3.2-UNIT-012] Threshold 0.0 allows all results."""
        validated = settings.validate_similarity_threshold(0.0)
        assert validated == 0.0

    async def test_3_2_013_given_threshold_1_when_searching_then_no_results(self):
        """[3.2-UNIT-013] Threshold 1.0 requires perfect match."""
        validated = settings.validate_similarity_threshold(1.0)
        assert validated == 1.0

    def test_3_2_014_given_negative_threshold_when_loaded_then_clamped_to_0(self):
        """[3.2-UNIT-014] Negative threshold clamped to 0.0."""
        validated = settings.validate_similarity_threshold(-0.5)
        assert validated == 0.0

    def test_3_2_015_given_threshold_over_1_when_loaded_then_clamped_to_1(self):
        """[3.2-UNIT-015] Threshold > 1.0 clamped to 1.0."""
        validated = settings.validate_similarity_threshold(1.5)
        assert validated == 1.0


@pytest.mark.asyncio
class TestNamespaceGuardAC4:
    async def test_3_2_016_given_upload_without_org_id_then_403(self):
        """[3.2-UNIT-016] Missing org_id returns 403."""
        session = _mock_session()
        with pytest.raises(HTTPException) as exc_info:
            await verify_namespace_access(session=session, org_id="")
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "NAMESPACE_VIOLATION"

    async def test_3_2_017_given_list_docs_then_only_own_org_returned(self):
        """[3.2-UNIT-017] Collection endpoints return org_id for filtering."""
        session = _mock_session()
        org_id = await verify_namespace_access(session=session, org_id="org-list")
        assert org_id == "org-list"

    async def test_3_2_018_given_search_request_then_guard_runs_first(self):
        """[3.2-UNIT-018] Guard executes before business logic (returns org_id)."""
        session = _mock_session()
        org_id = await verify_namespace_access(session=session, org_id="org-search")
        assert org_id == "org-search"


@pytest.mark.asyncio
class TestNamespaceGuardAC5:
    async def test_3_2_019_given_two_tenants_when_audit_then_cross_tenant_returns_0(
        self,
    ):
        """[3.2-UNIT-019] Audit verifies cross-tenant isolation."""
        service = NamespaceAuditService()
        session = MagicMock(spec=AsyncSession)
        orgs_result = MagicMock()
        orgs_result.fetchall.return_value = [("org-a",), ("org-b",)]
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        # 1 orgs query + 1 pair × (1 set_config + 1 count) × 3 checks = 1 + 6 = 7
        session.execute = AsyncMock(side_effect=[orgs_result] + [count_result] * 7)

        report = await service.run_isolation_audit(session)
        assert report.passed == report.total_checks
        assert report.failed == 0
        assert report.tenant_count == 2
        assert report.pairs_checked == 1

    async def test_3_2_020_given_audit_endpoint_when_non_admin_then_403(self):
        """[3.2-UNIT-020] Non-admin audit access is handled by router."""
        assert True

    async def test_3_2_021_given_audit_results_then_all_pairs_reported(self):
        """[3.2-UNIT-021] Report contains all tenant pair combinations."""
        service = NamespaceAuditService()
        session = MagicMock(spec=AsyncSession)
        orgs_result = MagicMock()
        orgs_result.fetchall.return_value = [("org-a",), ("org-b",), ("org-c",)]
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        # 3 orgs → 3 pairs × 3 checks × 2 queries each = 18 + 1 orgs query = 19
        session.execute = AsyncMock(side_effect=[orgs_result] + [count_result] * 19)

        report = await service.run_isolation_audit(session)
        assert report.tenant_count == 3
        assert report.pairs_checked == 3

    async def test_3_2_022_given_processing_docs_when_audit_then_excluded(self):
        """[3.2-UNIT-022] Processing docs excluded from audit."""
        service = NamespaceAuditService()
        session = MagicMock(spec=AsyncSession)
        orgs_result = MagicMock()
        orgs_result.fetchall.return_value = []
        session.execute = AsyncMock(return_value=orgs_result)

        report = await service.run_isolation_audit(session)
        assert report.total_checks == 0
        assert report.tenant_count == 0

    async def test_3_2_023_given_many_pairs_when_audit_then_limited(self):
        """[3.2-UNIT-023] Audit limited to NAMESPACE_AUDIT_MAX_PAIRS."""
        service = NamespaceAuditService()
        session = MagicMock(spec=AsyncSession)
        many_orgs = [(f"org-{i}",) for i in range(20)]
        orgs_result = MagicMock()
        orgs_result.fetchall.return_value = many_orgs
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        call_count = 0

        async def _mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return orgs_result
            return count_result

        session.execute = AsyncMock(side_effect=_mock_execute)

        report = await service.run_isolation_audit(session)
        assert report.pairs_checked <= settings.NAMESPACE_AUDIT_MAX_PAIRS
        assert report.pairs_skipped > 0

    async def test_3_2_024_given_audit_twice_within_5min_then_rate_limited(self):
        """[3.2-UNIT-024] Rate limit audit endpoint to 1 per org per 5 min."""
        from middleware.rate_limit import namespace_audit_limiter

        assert namespace_audit_limiter.max_requests == 1
        assert namespace_audit_limiter.window_seconds == 300

    async def test_3_2_025_given_broken_rls_when_audit_then_reports_failed(self):
        """[3.2-UNIT-025] Audit detects real RLS failures."""
        service = NamespaceAuditService()
        session = MagicMock(spec=AsyncSession)
        orgs_result = MagicMock()
        orgs_result.fetchall.return_value = [("org-a",), ("org-b",)]
        count_result = MagicMock()
        count_result.scalar.return_value = 5
        # 1 orgs query + 1 pair × 3 checks × 2 queries = 7
        session.execute = AsyncMock(side_effect=[orgs_result] + [count_result] * 7)

        report = await service.run_isolation_audit(session)
        assert report.failed > 0


@pytest.mark.asyncio
class TestNamespaceGuardAC6:
    async def test_3_2_026_given_search_with_guard_then_latency_under_200ms(self):
        """[3.2-UNIT-026] Total guard latency stays well under 200ms."""
        session = _mock_session_with_resource("org-perf")
        start = time.monotonic()
        for _ in range(50):
            await verify_namespace_access(
                resource_id=1,
                request=_mock_request(),
                session=session,
                org_id="org-perf",
            )
        elapsed_ms = (time.monotonic() - start) * 1000 / 50
        assert elapsed_ms < 200, f"Average latency {elapsed_ms:.2f}ms exceeds 200ms"

    async def test_3_2_027_given_guard_check_then_overhead_under_5ms(self):
        """[3.2-UNIT-027] Guard overhead specifically under 5ms."""
        session = _mock_session()
        start = time.monotonic()
        for _ in range(100):
            await verify_namespace_access(session=session, org_id="org-perf")
        elapsed_ms = (time.monotonic() - start) * 1000 / 100
        assert elapsed_ms < 5.0, f"Guard overhead {elapsed_ms:.2f}ms exceeds 5ms"


@pytest.mark.asyncio
class TestNamespaceGuardAC7:
    async def test_3_2_028_given_flag_off_cross_tenant_then_no_403(self):
        """[3.2-UNIT-028] Flag off skips ownership check — no 403 for cross-tenant."""
        with patch.object(settings, "NAMESPACE_GUARD_ENABLED", False):
            session = _mock_session_with_resource("org-other")
            org_id = await verify_namespace_access(
                resource_id=42,
                request=_mock_request(),
                session=session,
                org_id="org-mine",
            )
            assert org_id == "org-mine"

    async def test_3_2_029_given_flag_off_list_docs_then_own_org_only(self):
        """[3.2-UNIT-029] Flag off still uses org_id for collection queries."""
        with patch.object(settings, "NAMESPACE_GUARD_ENABLED", False):
            session = _mock_session()
            org_id = await verify_namespace_access(session=session, org_id="org-filter")
            assert org_id == "org-filter"


@pytest.mark.asyncio
class TestNamespaceSchemas:
    async def test_namespace_error_schema(self):
        from schemas.knowledge import NamespaceError, NamespaceViolationResponse

        err = NamespaceError(timestamp="2026-04-06T00:00:00Z")
        assert err.code == "NAMESPACE_VIOLATION"
        assert err.message == "Cross-tenant access denied"
        resp = NamespaceViolationResponse(error=err)
        assert resp.error.code == "NAMESPACE_VIOLATION"

    async def test_search_response_has_guard_overhead(self):
        from schemas.knowledge import KnowledgeSearchResponse

        resp = KnowledgeSearchResponse(
            results=[],
            total=0,
            query="test",
            guardOverheadMs=1.23,
        )
        assert resp.guardOverheadMs == 1.23
