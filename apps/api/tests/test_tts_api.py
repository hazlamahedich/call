"""
[2.3-UNIT-010] Test TTS API endpoints.
"""

import pytest
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


class TestProvidersHealthEndpoint:
    def test_returns_health_status(self):
        app = _mock_app()
        client = TestClient(app, raise_server_exceptions=False)
        mock_orch = MagicMock()
        mock_orch.get_providers_health = AsyncMock(
            return_value={"elevenlabs": True, "cartesia": False}
        )
        with patch("routers.tts.get_tts_orchestrator", return_value=mock_orch):
            response = client.get("/tts/providers/health")
        assert response.status_code == 200
        data = response.json()
        assert data["providers"]["elevenlabs"] is True
        assert data["providers"]["cartesia"] is False


class TestSessionStatusEndpoint:
    def test_returns_session_status(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = ("vci-1",)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        app = _mock_app(mock_db)
        client = TestClient(app, raise_server_exceptions=False)
        mock_orch = MagicMock()
        mock_orch.get_session_provider = MagicMock(return_value="elevenlabs")
        mock_orch.get_session_latency_history = MagicMock(
            return_value=[100.0, 200.0, 150.0]
        )
        with patch("routers.tts.get_tts_orchestrator", return_value=mock_orch):
            response = client.get("/tts/session/1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["activeProvider"] == "elevenlabs"
        assert len(data["latencyHistory"]) == 3

    def test_call_not_found_returns_404(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        app = _mock_app(mock_db)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/tts/session/999/status")
        assert response.status_code == 404

    def test_handles_null_vapi_call_id(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = (None,)
        mock_db.execute = AsyncMock(return_value=mock_result)

        app = _mock_app(mock_db)
        client = TestClient(app, raise_server_exceptions=False)
        mock_orch = MagicMock()
        mock_orch.get_session_provider = MagicMock(return_value="elevenlabs")
        with patch("routers.tts.get_tts_orchestrator", return_value=mock_orch):
            response = client.get("/tts/session/5/status")
        assert response.status_code == 200
        data = response.json()
        assert data["requestCount"] == 0
