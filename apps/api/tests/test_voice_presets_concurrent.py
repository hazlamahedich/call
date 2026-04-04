"""Concurrent preset selection integration tests.

Tests race conditions when multiple users select the same preset
simultaneously. Validates row-level locking prevents conflicts.
"""

import asyncio
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.agent import Agent
from models.voice_preset import VoicePreset


@pytest.fixture
def preset_factory_concurrent(db_session: AsyncSession):
    """Factory for creating test presets."""
    async def _create(
        org_id: str,
        name: str,
        use_case: str = "sales",
        voice_id: str = "test_voice",
        speech_speed: float = 1.0,
        stability: float = 0.8,
        temperature: float = 0.7,
        is_active: bool = True,
        sort_order: int = 0,
    ) -> VoicePreset:
        preset = VoicePreset(
            org_id=org_id,
            name=name,
            use_case=use_case,
            voice_id=voice_id,
            speech_speed=speech_speed,
            stability=stability,
            temperature=temperature,
            is_active=is_active,
            sort_order=sort_order,
        )
        db_session.add(preset)
        await db_session.commit()
        await db_session.refresh(preset)
        return preset

    return _create


@pytest.fixture
def auth_token_for_org_concurrent():
    """Generate auth token for a test org."""
    def _token(org_id: str) -> str:
        # Mock JWT token with org_id claim
        import jwt
        payload = {
            "org_id": org_id,
            "sub": "test_user",
            "exp": 9999999999,
        }
        # Use test secret from settings
        from config.settings import settings
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    return _token


@pytest.mark.asyncio
async def test_concurrent_preset_selection(
    db_session: AsyncSession,
    preset_factory_concurrent,
    auth_token_for_org_concurrent,
):
    """Test multiple concurrent preset selections don't cause race conditions.

    Story 2.6 - HIGH PRIORITY TEST
    Risk: Race condition on agent update when multiple requests select same preset
    Mitigation: FOR UPDATE row-level lock in select_preset endpoint
    """
    # Create test preset
    preset = await preset_factory_concurrent(
        org_id="org1",
        name="Concurrent Test Preset",
        use_case="sales",
    )
    token = auth_token_for_org_concurrent("org1")

    async def select_preset():
        """Select preset concurrently."""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        response = client.post(
            f"/api/v1/voice-presets/{preset.id}/select",
            headers={"Authorization": f"Bearer {token}"},
        )
        return response

    # Launch concurrent selection requests
    num_requests = 5
    tasks = [select_preset() for _ in range(num_requests)]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    # All requests should succeed without conflicts
    successful_responses = [r for r in responses if isinstance(r, Exception) is False and r.status_code == 200]

    assert len(successful_responses) == num_requests, f"Expected {num_requests} successful responses, got {len(successful_responses)}"

    # Verify agent has preset configured
    result = await db_session.execute(
        select(Agent).where(Agent.org_id == "org1")
    )
    agent = result.scalar_one_or_none()

    assert agent is not None
    assert agent.preset_id == preset.id
    assert agent.speech_speed == preset.speech_speed
    assert agent.stability == preset.stability
    assert agent.temperature == preset.temperature
    assert agent.use_advanced_mode is False


@pytest.mark.asyncio
async def test_concurrent_preset_selection_different_presets(
    db_session: AsyncSession,
    preset_factory_concurrent,
    auth_token_for_org_concurrent,
):
    """Test concurrent selections of different presets don't conflict.

    Last write should win due to row-level locking.
    """
    # Create two test presets
    preset1 = await preset_factory_concurrent(
        org_id="org1",
        name="Preset 1",
        use_case="sales",
        speech_speed=1.0,
    )
    preset2 = await preset_factory_concurrent(
        org_id="org1",
        name="Preset 2",
        use_case="support",
        speech_speed=1.2,
    )
    token = auth_token_for_org_concurrent("org1")

    async def select_preset(preset_id: int):
        """Select preset concurrently."""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        response = client.post(
            f"/api/v1/voice-presets/{preset_id}/select",
            headers={"Authorization": f"Bearer {token}"},
        )
        return response

    # Launch concurrent selections for different presets
    tasks = [
        select_preset(preset1.id),
        select_preset(preset2.id),
        select_preset(preset1.id),  # Select preset1 again
    ]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    # All requests should succeed
    successful_responses = [r for r in responses if isinstance(r, Exception) is False and r.status_code == 200]
    assert len(successful_responses) == 3

    # Verify agent has final preset (last write wins)
    result = await db_session.execute(
        select(Agent).where(Agent.org_id == "org1")
    )
    agent = result.scalar_one_or_none()

    assert agent is not None
    # Last selection should be preset1
    assert agent.preset_id == preset1.id


@pytest.mark.asyncio
async def test_concurrent_advanced_config_saves(
    db_session: AsyncSession,
    auth_token_for_org_concurrent,
):
    """Test concurrent advanced config saves don't cause conflicts.

    Validates race condition handling in save_advanced_config endpoint.
    """
    token = auth_token_for_org_concurrent("org1")

    async def save_advanced_config(speech_speed: float):
        """Save advanced config concurrently."""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        response = client.post(
            "/api/v1/agent-config/advanced",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "speech_speed": speech_speed,
                "stability": 0.8,
                "temperature": 0.7,
            },
        )
        return response

    # Launch concurrent config saves with different speeds
    num_requests = 5
    speeds = [1.0, 1.2, 1.5, 1.8, 2.0]
    tasks = [save_advanced_config(speed) for speed in speeds]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    # All requests should succeed
    successful_responses = [r for r in responses if isinstance(r, Exception) is False and r.status_code == 200]
    assert len(successful_responses) == num_requests

    # Verify agent has one of the configs (last write wins)
    result = await db_session.execute(
        select(Agent).where(Agent.org_id == "org1")
    )
    agent = result.scalar_one_or_none()

    assert agent is not None
    assert agent.use_advanced_mode is True
    assert agent.preset_id is None  # No preset when using advanced mode
    assert agent.speech_speed in speeds
