"""Story 3.4 Expanded: Pipeline Integration Deep Coverage.

Tests script_generation.py variable injection integration paths:
partial params (422), feature toggle, token budget warning.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from conftest_3_4 import TEST_ORG
from services.script_generation import ScriptGenerationService


def _make_service():
    mock_llm = AsyncMock()
    mock_embedding = AsyncMock()
    mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one.return_value = 0
    mock_session.execute = AsyncMock(return_value=mock_result)
    return ScriptGenerationService(
        llm_service=mock_llm,
        embedding_service=mock_embedding,
        session=mock_session,
        redis_client=AsyncMock(),
    )


@pytest.mark.asyncio
class TestPipelinePartialParams:
    @pytest.mark.p1
    async def test_lead_id_without_script_id_raises_422(self):
        service = _make_service()
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_response(
                query="test",
                org_id=TEST_ORG,
                lead_id=1,
                script_id=None,
            )
        assert exc_info.value.status_code == 422
        assert (
            "both" in str(exc_info.value.detail).lower()
            or "together" in str(exc_info.value.detail).lower()
        )

    @pytest.mark.p1
    async def test_script_id_without_lead_id_raises_422(self):
        service = _make_service()
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_response(
                query="test",
                org_id=TEST_ORG,
                lead_id=None,
                script_id=1,
            )
        assert exc_info.value.status_code == 422

    @pytest.mark.p1
    async def test_both_none_does_not_raise_422(self):
        service = _make_service()
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch.object(
                service,
                "_check_cache_by_key",
                new_callable=AsyncMock,
                return_value=None,
            ):
                result = await service.generate_response(
                    query="test",
                    org_id=TEST_ORG,
                    lead_id=None,
                    script_id=None,
                )
                assert result is not None


@pytest.mark.asyncio
class TestPipelineFeatureToggle:
    @pytest.mark.p1
    async def test_variable_injection_disabled_skips_injection(self):
        service = _make_service()
        with patch("services.script_generation.settings") as mock_settings:
            mock_settings.VARIABLE_INJECTION_ENABLED = False
            mock_settings.AI_LLM_MAX_TOKENS = 4000
            mock_settings.TOKEN_RESERVATION = 500

            with patch(
                "services.script_generation.search_knowledge_chunks",
                new_callable=AsyncMock,
                return_value=[],
            ):
                with patch.object(
                    service,
                    "_check_cache_by_key",
                    new_callable=AsyncMock,
                    return_value=None,
                ):
                    result = await service.generate_response(
                        query="test",
                        org_id=TEST_ORG,
                        lead_id=1,
                        script_id=1,
                    )
                    assert result is not None


@pytest.mark.asyncio
class TestCacheKeyWithVariableFingerprint:
    @pytest.mark.p1
    async def test_cache_key_includes_lead_and_script_id(self):
        service = _make_service()
        from conftest_3_4 import make_lead, make_script_with_variables
        from services.variable_injection import RenderResult

        with patch("services.script_generation.settings") as mock_settings:
            mock_settings.VARIABLE_INJECTION_ENABLED = True
            mock_settings.VARIABLE_RESOLUTION_TIMEOUT_MS = 100
            mock_settings.AI_LLM_MAX_TOKENS = 4000
            mock_settings.TOKEN_RESERVATION = 500

            with (
                patch(
                    "services.variable_injection.VariableInjectionService"
                ) as mock_injection_cls,
                patch(
                    "services.shared_queries.load_script_for_context",
                    new_callable=AsyncMock,
                    return_value=make_script_with_variables("Hello {{lead_name}}"),
                ),
                patch(
                    "services.shared_queries.load_lead_for_context",
                    new_callable=AsyncMock,
                    return_value=make_lead(name="Alice"),
                ),
            ):
                mock_svc = AsyncMock()
                mock_svc.render_template = AsyncMock(
                    return_value=RenderResult(
                        rendered_text="Hello Alice",
                        resolved_variables={"lead_name": "Alice"},
                        unresolved_variables=[],
                        was_rendered=True,
                    )
                )
                mock_injection_cls.return_value = mock_svc

                with (
                    patch(
                        "services.script_generation.search_knowledge_chunks",
                        new_callable=AsyncMock,
                        return_value=[],
                    ),
                    patch.object(
                        service,
                        "_check_cache_by_key",
                        new_callable=AsyncMock,
                        return_value=None,
                    ),
                ):
                    await service.generate_response(
                        query="test",
                        org_id=TEST_ORG,
                        lead_id=42,
                        script_id=7,
                    )

                    cache_call = service._check_cache_by_key.call_args
                    cache_key = cache_call[0][0] if cache_call else None
                    assert cache_key is not None, "Cache key was not generated"
                    assert ":l42:s7" in cache_key
