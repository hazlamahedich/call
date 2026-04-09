"""AC7: Tenant isolation tests for factual hook verification."""

from unittest.mock import AsyncMock, patch

import pytest

from services.factual_hook import FactualHookService


@pytest.mark.asyncio
class TestTenantIsolation:
    async def test_3_6_unit_021_given_org_a_when_verifying_then_org_b_excluded(
        self, factual_hook_service
    ):
        calls = []

        async def capture_search(*args, **kwargs):
            calls.append({"args": args, "kwargs": kwargs})
            return [{"chunk_id": 1, "content": "data", "similarity": 0.85}]

        with patch(
            "services.factual_hook.search_knowledge_chunks",
            side_effect=capture_search,
        ):
            await factual_hook_service._verify_claim(
                "Our revenue grew 32%.",
                "org-tenant-a",
                [10, 20],
                0.75,
            )
            assert len(calls) == 1
            assert calls[0]["args"][2] == "org-tenant-a"
            assert calls[0]["kwargs"].get("knowledge_base_ids") == [10, 20]

    async def test_3_6_unit_021b_given_different_orgs_when_verifying_then_scoped_separately(
        self, mock_session, mock_llm, mock_embedding
    ):
        svc = FactualHookService(mock_session, mock_llm, mock_embedding)

        org_a_calls = []
        org_b_calls = []

        async def search_for_org(*args, **kwargs):
            org_id = args[2]
            if org_id == "org-a":
                org_a_calls.append(kwargs)
                return [{"chunk_id": 1, "content": "a-data", "similarity": 0.9}]
            else:
                org_b_calls.append(kwargs)
                return []

        with patch(
            "services.factual_hook.search_knowledge_chunks",
            side_effect=search_for_org,
        ):
            r_a = await svc._verify_claim("Revenue 32%.", "org-a", None, 0.75)
            r_b = await svc._verify_claim("Revenue 32%.", "org-b", None, 0.75)

        assert r_a.is_supported is True
        assert r_b.is_supported is False
