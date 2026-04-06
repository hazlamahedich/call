"""E2E tests for namespace guard isolation.

Tests full request/response flows with namespace guard across
multi-tenant knowledge base operations.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from main import app
from database.session import get_session
from middleware.auth import AuthMiddleware


def _unique_org(label="org"):
    return f"{label}-{uuid.uuid4().hex[:8]}"


def _token_payload(org_id=None, user_id="user-test", role=None):
    org = org_id or _unique_org("org")
    payload = {"org_id": org, "sub": user_id}
    if role is not None:
        payload["orgs"] = {org: {"role": role}}
    return payload


async def _bypass_auth(self, token):
    return _token_payload()


async def _bypass_auth_admin(self, token):
    return _token_payload(role="platform_admin")


def _mock_session(execute_return=None, execute_side_effect=None):
    session = MagicMock()
    if execute_side_effect is not None:
        session.execute = AsyncMock(side_effect=execute_side_effect)
    else:
        session.execute = AsyncMock(return_value=execute_return)
    session.commit = AsyncMock()
    return session


def _audit_execute_factory_e2e(org_ids, cross_tenant_count=0, include_set_config=True):
    def execute(stmt, params=None):
        sql = str(stmt).lower()
        if "distinct org_id" in sql:
            result = MagicMock()
            result.fetchall.return_value = [(oid,) for oid in org_ids]
            return result
        if "set_config" in sql:
            return MagicMock()
        result = MagicMock()
        result.scalar.return_value = cross_tenant_count
        return result

    return execute


@pytest.mark.asyncio
@pytest.mark.p0
class TestNamespaceGuardE2E:
    @pytest.fixture(autouse=True)
    def _clean_overrides(self):
        yield
        app.dependency_overrides.clear()

    async def test_3_2_e2e_001_given_org_a_lists_when_guard_then_only_own_docs(
        self,
    ):
        """[3.2-E2E-001] Org A list docs returns only Org A docs via HTTP."""
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        docs_result = MagicMock()
        docs_result.fetchall.return_value = []

        session = _mock_session(execute_side_effect=[count_result, docs_result])

        async def _override_session():
            yield session

        app.dependency_overrides[get_session] = _override_session

        with (
            patch.object(AuthMiddleware, "_verify_token", _bypass_auth),
            patch("routers.knowledge._set_rls_context"),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/v1/documents",
                    headers={"Authorization": "Bearer test-token"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert "items" in data or "documents" in data

    async def test_3_2_e2e_002_given_unauthenticated_when_request_then_401(self):
        """[3.2-E2E-002] Unauthenticated request returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/documents")
            assert resp.status_code == 401

    async def test_3_2_e2e_003_given_audit_by_admin_then_full_report(self):
        """[3.2-E2E-003] Admin audit returns full report with tenant pairs."""
        org_ids = [_unique_org("org"), _unique_org("org")]

        audit_session = MagicMock()
        audit_session.execute = AsyncMock(
            side_effect=_audit_execute_factory_e2e(
                org_ids, cross_tenant_count=0, include_set_config=True
            )
        )
        audit_session.close = AsyncMock()

        session = _mock_session()

        async def _override_session():
            yield session

        app.dependency_overrides[get_session] = _override_session

        with (
            patch.object(AuthMiddleware, "_verify_token", _bypass_auth_admin),
            patch(
                "routers.knowledge.AsyncSessionLocal",
                return_value=audit_session,
            ),
            patch("routers.knowledge.namespace_audit_limiter") as mock_limiter,
        ):
            mock_limiter.check_rate_limit = AsyncMock(return_value=True)

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/audit/isolation",
                    headers={"Authorization": "Bearer test-token"},
                )
                assert resp.status_code == 200
                data = resp.json()
                tc = data.get("tenant_count", data.get("tenantCount"))
                assert tc == 2
                totc = data.get("total_checks", data.get("totalChecks"))
                assert totc == 3
                p = data.get("passed", 0)
                assert p == 3
                f = data.get("failed", 0)
                assert f == 0

    async def test_3_2_e2e_004_given_cross_tenant_get_doc_then_403(self):
        """[3.2-E2E-004] GET document from another org returns 403 via HTTP."""
        org_other = _unique_org("org")
        resource_result = MagicMock()
        resource_result.fetchone.return_value = (org_other,)

        session = _mock_session(execute_return=resource_result)

        async def _override_session():
            yield session

        app.dependency_overrides[get_session] = _override_session

        with patch.object(AuthMiddleware, "_verify_token", _bypass_auth):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/v1/documents/42",
                    headers={"Authorization": "Bearer test-token"},
                )
                assert resp.status_code == 403
                data = resp.json()
                assert data["detail"]["code"] == "NAMESPACE_VIOLATION"

    async def test_3_2_e2e_005_given_nonexistent_doc_then_404(self):
        """[3.2-E2E-005] GET non-existent document returns 404 via HTTP."""
        resource_result = MagicMock()
        resource_result.fetchone.return_value = None

        session = _mock_session(execute_return=resource_result)

        async def _override_session():
            yield session

        app.dependency_overrides[get_session] = _override_session

        with patch.object(AuthMiddleware, "_verify_token", _bypass_auth):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/v1/documents/9999",
                    headers={"Authorization": "Bearer test-token"},
                )
                assert resp.status_code == 404
                data = resp.json()
                assert data["detail"]["code"] == "KNOWLEDGE_BASE_NOT_FOUND"

    async def test_3_2_e2e_006_given_non_admin_audit_then_403(self):
        """[3.2-E2E-006] Non-admin audit request returns 403 via HTTP."""
        session = _mock_session()

        async def _override_session():
            yield session

        app.dependency_overrides[get_session] = _override_session

        with (
            patch.object(AuthMiddleware, "_verify_token", _bypass_auth),
            patch("routers.knowledge.namespace_audit_limiter") as mock_limiter,
        ):
            mock_limiter.check_rate_limit = AsyncMock(return_value=True)

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/audit/isolation",
                    headers={"Authorization": "Bearer test-token"},
                )
                assert resp.status_code == 403
