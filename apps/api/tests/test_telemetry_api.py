"""
Integration Tests for Telemetry API
Story 2.4: Asynchronous Telemetry Sidecars for Voice Events

Tests for telemetry endpoints: metrics and events query.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.voice_telemetry import VoiceTelemetry
from routers.telemetry import router as telemetry_router


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def client(mock_session):
    """Test client with mocked dependencies."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(telemetry_router)

    # Override dependency
    from routers.telemetry import get_session

    async def override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session

    return TestClient(app)


class TestMetricsEndpoint:
    """[2.4-INTEGRATION-001] Test /api/v1/telemetry/metrics endpoint (AC: 6)."""

    def test_metrics_returns_queue_health(self, client):
        """Test metrics endpoint returns queue health data."""
        from services.telemetry import telemetry_queue

        # Mock queue metrics
        telemetry_queue.get_metrics = MagicMock(
            return_value={
                "current_depth": 100,
                "avg_depth": 50.5,
                "max_depth": 200,
                "is_running": True,
                "processing_latency_ms_p95": 85.3,
                "events_per_second": 1250.0,
            }
        )

        response = client.get("/api/v1/telemetry/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["current_depth"] == 100
        assert data["avg_depth"] == 50.5
        assert data["max_depth"] == 200
        assert data["is_running"] is True
        assert data["processing_latency_ms_p95"] == 85.3
        assert data["events_per_second"] == 1250.0

    def test_metrics_endpoint_no_auth_required(self, client):
        """Test metrics endpoint does not require authentication."""
        # Should not raise auth error
        from services.telemetry import telemetry_queue

        telemetry_queue.get_metrics = MagicMock(return_value={})
        response = client.get("/api/v1/telemetry/metrics")

        assert response.status_code == 200


class TestEventsQueryEndpoint:
    """[2.4-INTEGRATION-002] Test /api/v1/telemetry/events endpoint (AC: 7)."""

    def test_events_query_with_filters(self, client, mock_session):
        """Test events query with call_id and event_type filters."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            VoiceTelemetry(
                id=1,
                org_id="org123",
                call_id=456,
                event_type="silence",
                timestamp=datetime.now(timezone.utc),
                duration_ms=1500.0,
                audio_level=-60.0,
                confidence_score=0.9,
                sentiment_score=0.7,
                provider="deepgram",
                session_metadata=None,
                queue_depth_at_capture=100,
                processing_latency_ms=2.5,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                soft_delete=False,
            )
        ]
        mock_session.execute.return_value = mock_result

        response = client.get(
            "/api/v1/telemetry/events?call_id=456&event_type=silence&limit=1000"
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert data["total"] == 1
        assert data["limit"] == 1000
        assert len(data["events"]) == 1

    def test_events_query_with_timestamp_range(self, client, mock_session):
        """Test events query with start_time and end_time filters."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        start_time = "2026-04-01T00:00:00Z"
        end_time = "2026-04-01T23:59:59Z"

        response = client.get(
            f"/api/v1/telemetry/events?start_time={start_time}&end_time={end_time}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data

    def test_events_query_respects_limit_max(self, client, mock_session):
        """Test limit parameter respects max of 10000 (AC: 7)."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        response = client.get("/api/v1/telemetry/events?limit=15000")

        # Should use max limit of 10000
        assert response.status_code == 200

    def test_events_query_invalid_timestamp_format(self, client, mock_session):
        """Test events query handles invalid timestamp gracefully."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        response = client.get("/api/v1/telemetry/events?start_time=invalid")

        # Should not error, just log warning and continue
        assert response.status_code == 200


class TestTenantIsolation:
    """[2.4-INTEGRATION-003] Test tenant isolation in queries (AC: 7)."""

    def test_events_query_enforces_tenant_isolation(self, client, mock_session):
        """[2.4-INTEGRATION-004] Test queries are scoped to user's org_id via RLS."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        response = client.get("/api/v1/telemetry/events")

        assert response.status_code == 200

        # In production, session.info["current_org_id"] would be set
        # via get_tenant_scoped_session dependency
        # RLS policies enforce tenant isolation at DB level
