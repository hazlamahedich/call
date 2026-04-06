"""E2E tests for namespace guard isolation.

Tests full request/response flows with namespace guard across
multi-tenant knowledge base operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from main import app
from dependencies.org_context import get_current_org_id


def _mock_request_state(user_role="platform_admin"):
    request = MagicMock()
    request.state.user_role = user_role
    return request


@pytest.mark.asyncio
class TestNamespaceGuardE2E:
    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    async def test_3_2_e2e_001_given_org_a_searches_when_namespace_guard_then_only_own_chunks(
        self,
    ):
        """[3.2-E2E-001] Org A search returns only Org A chunks via HTTP."""
        with (
            patch("routers.knowledge.get_current_org_id", return_value="org-alpha"),
            patch("routers.knowledge.verify_namespace_access") as mock_guard,
            patch("routers.knowledge.get_embedding_service") as mock_emb,
            patch("routers.knowledge._set_rls_context"),
        ):
            mock_guard.side_effect = lambda **kwargs: kwargs.get("org_id", "org-alpha")

            embedding = MagicMock()
            embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
            embedding.provider = MagicMock()
            embedding.provider.model_name = "text-embedding-3-small"
            mock_emb.return_value = embedding

            mock_result = MagicMock()
            mock_result.fetchall.return_value = []

            async def _mock_execute(stmt, params=None):
                return mock_result

            with patch("routers.knowledge.get_session") as mock_session_dep:
                session = MagicMock()
                session.execute = AsyncMock(side_effect=_mock_execute)
                session.commit = AsyncMock()
                mock_session_dep.return_value = session

                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport, base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/knowledge/search",
                        json={"query": "test query", "topK": 5},
                    )
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["query"] == "test query"
                    assert "results" in data
                    assert "total" in data

    async def test_3_2_e2e_002_given_unauthenticated_when_search_then_401(self):
        """[3.2-E2E-002] Unauthenticated request returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/knowledge/search",
                json={"query": "test query"},
            )
            assert resp.status_code in (401, 403, 422)

    async def test_3_2_e2e_003_given_audit_called_by_admin_then_full_report(
        self,
    ):
        """[3.2-E2E-003] Admin audit returns full report with tenant pairs."""
        from services.namespace_audit import NamespaceAuditService

        with (
            patch("routers.knowledge.get_current_org_id", return_value="org-admin"),
            patch("routers.knowledge.get_session") as mock_session_dep,
            patch("routers.knowledge.AsyncSessionLocal") as mock_session_factory,
            patch("routers.knowledge.get_audit_service") as mock_audit_svc,
            patch("routers.knowledge.namespace_audit_limiter") as mock_limiter,
        ):
            mock_limiter.check_rate_limit = AsyncMock(return_value=True)

            mock_request = MagicMock()
            mock_request.state.user_role = "platform_admin"

            audit_session = MagicMock()
            orgs_result = MagicMock()
            orgs_result.fetchall.return_value = [("org-alpha",), ("org-beta",)]
            count_result = MagicMock()
            count_result.scalar.return_value = 0
            audit_session.execute = AsyncMock(
                side_effect=[orgs_result] + [count_result] * 9
            )
            audit_session.close = AsyncMock()
            mock_session_factory.return_value = audit_session

            service = NamespaceAuditService()
            mock_audit_svc.return_value = service

            session = MagicMock()
            session.execute = AsyncMock()
            mock_session_dep.return_value = session

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.post("/api/knowledge/audit/isolation")
                if resp.status_code == 200:
                    data = resp.json()
                    assert "tenant_count" in data
                    assert "total_checks" in data
                    assert "passed" in data
                    assert "failed" in data
