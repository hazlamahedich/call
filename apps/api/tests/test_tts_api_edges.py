"""
[2.3-UNIT-015] Test TTS API edge cases — single-element p95, latency history eviction.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from dependencies.org_context import get_current_org_id
from database.session import get_session


async def _mock_org_id():
    return "org-1"


def _mock_app(mock_db=None):
    from routers.tts import router

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_org_id] = _mock_org_id
    if mock_db is not None:

        async def _override_session():
            yield mock_db

        app.dependency_overrides[get_session] = _override_session
    return app


class TestSessionStatusP95Single:
    """
    [2.3-UNIT-015_P1] P95 calculation with single latency entry uses idx=0.
    """

    def test_P1_single_latency_entry_uses_first_element(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = ("vci-p95",)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        app = _mock_app(mock_db)
        client = TestClient(app, raise_server_exceptions=False)
        mock_orch = MagicMock()
        mock_orch.get_session_provider = MagicMock(return_value="elevenlabs")
        mock_orch.get_session_latency_history = MagicMock(return_value=[250.0])
        with patch(
            "routers.tts.get_tts_orchestrator",
            new_callable=AsyncMock,
            return_value=mock_orch,
        ):
            response = client.get("/tts/session/1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["p95LatencyMs"] == 250.0
        assert data["requestCount"] == 1

    def test_P1_many_latency_entries_computes_p95(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = ("vci-p95-many",)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        app = _mock_app(mock_db)
        client = TestClient(app, raise_server_exceptions=False)
        mock_orch = MagicMock()
        mock_orch.get_session_provider = MagicMock(return_value="elevenlabs")
        latencies = [
            100.0,
            200.0,
            300.0,
            400.0,
            500.0,
            600.0,
            700.0,
            800.0,
            900.0,
            1000.0,
        ]
        mock_orch.get_session_latency_history = MagicMock(return_value=latencies)
        with patch(
            "routers.tts.get_tts_orchestrator",
            new_callable=AsyncMock,
            return_value=mock_orch,
        ):
            response = client.get("/tts/session/2/status")
        assert response.status_code == 200
        data = response.json()
        assert data["p95LatencyMs"] is not None
        assert data["p95LatencyMs"] == 900.0
