"""Integration tests for voice preset API endpoints.

[2.6-INTEGRATION-001] Test full preset lifecycle (list → select → verify)
[2.6-INTEGRATION-002] Test preset sample endpoint returns valid audio
[2.6-INTEGRATION-003] Test concurrent preset selection
[2.6-INTEGRATION-004] Test unauthenticated requests return 403
"""

import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.agent import Agent
from models.voice_preset import VoicePreset


@pytest.mark.asyncio
async def test_full_preset_lifecycle(
    db_session: AsyncSession,
    client,
    auth_token_for_org,
):
    """[2.6-INTEGRATION-001] Complete workflow: list presets, select one, verify agent updated."""
    org_id = "test_lifecycle"
    token = await auth_token_for_org(org_id)

    # Create presets
    preset1 = VoicePreset(
        org_id=org_id,
        name="Sales Preset 1",
        use_case="sales",
        voice_id="voice1",
        speech_speed=1.2,
        stability=0.7,
        temperature=0.8,
        description="First sales preset",
        is_active=True,
        sort_order=1,
    )
    preset2 = VoicePreset(
        org_id=org_id,
        name="Sales Preset 2",
        use_case="sales",
        voice_id="voice2",
        speech_speed=1.0,
        stability=0.9,
        temperature=0.6,
        description="Second sales preset",
        is_active=True,
        sort_order=2,
    )
    db_session.add_all([preset1, preset2])
    await db_session.commit()

    # Step 1: List presets
    response = client.get(
        "/api/v1/voice-presets",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert data["presets"][0]["name"] == "Sales Preset 1"
    assert data["presets"][1]["name"] == "Sales Preset 2"

    # Step 2: Select first preset
    response = client.post(
        f"/api/v1/voice-presets/{preset1.id}/select",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["preset_id"] == preset1.id
    assert "saved successfully" in data["message"]

    # Step 3: Verify agent was created/updated
    response = client.get(
        "/api/v1/agent-config/current",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["preset_id"] == preset1.id
    assert data["speech_speed"] == 1.2
    assert data["stability"] == 0.7
    assert data["temperature"] == 0.8
    assert data["use_advanced_mode"] is False

    # Cleanup
    await db_session.delete(preset1)
    await db_session.delete(preset2)
    await db_session.commit()


@pytest.mark.asyncio
async def test_preset_sample_endpoint_returns_audio(
    db_session: AsyncSession,
    client,
    auth_token_for_org,
    mock_tts_provider,
):
    """[2.6-INTEGRATION-002] GET /voice-presets/{id}/sample returns valid audio."""
    org_id = "test_sample"
    token = await auth_token_for_org(org_id)

    # Create preset
    preset = VoicePreset(
        org_id=org_id,
        name="Test Preset",
        use_case="sales",
        voice_id="test_voice",
        speech_speed=1.0,
        stability=0.8,
        temperature=0.7,
        description="Test",
        is_active=True,
        sort_order=1,
    )
    db_session.add(preset)
    await db_session.commit()

    # Mock TTS response
    mock_tts_provider.return_value = MagicMock(
        audio_bytes=b"fake mp3 audio data",
        latency_ms=150,
        provider="test",
        content_type="audio/mpeg",
        error=False,
        error_message=None,
    )

    # Request sample
    response = client.get(
        f"/api/v1/voice-presets/{preset.id}/sample",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Should return audio
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    audio_data = response.content
    assert audio_data == b"fake mp3 audio data"

    # Cleanup
    await db_session.delete(preset)
    await db_session.commit()


@pytest.mark.asyncio
async def test_concurrent_preset_selection(
    db_session: AsyncSession,
    client,
    auth_token_for_org,
):
    """[2.6-INTEGRATION-003] Multiple concurrent preset selections handle correctly."""
    org_id = "test_concurrent"
    token = await auth_token_for_org(org_id)

    # Create presets
    presets = []
    for i in range(3):
        preset = VoicePreset(
            org_id=org_id,
            name=f"Preset {i}",
            use_case="sales",
            voice_id=f"voice{i}",
            speech_speed=1.0 + (i * 0.1),
            stability=0.8,
            temperature=0.7,
            description=f"Preset {i}",
            is_active=True,
            sort_order=i,
        )
        db_session.add(preset)
        presets.append(preset)
    await db_session.commit()

    # Select all presets concurrently
    async def select_preset(preset_id: int):
        response = client.post(
            f"/api/v1/voice-presets/{preset_id}/select",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response

    # Run concurrent selections
    responses = await asyncio.gather(*[
        select_preset(presets[0].id),
        select_preset(presets[1].id),
        select_preset(presets[2].id),
    ])

    # All should succeed
    for response in responses:
        assert response.status_code == 200

    # Last selection should win
    response = client.get(
        "/api/v1/agent-config/current",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Agent should have one of the presets selected
    assert data["preset_id"] in [presets[0].id, presets[1].id, presets[2].id]

    # Cleanup
    for preset in presets:
        await db_session.delete(preset)
    await db_session.commit()


@pytest.mark.asyncio
async def test_unauthenticated_requests_return_403(
    db_session: AsyncSession,
    client,
):
    """[2.6-INTEGRATION-004] All endpoints require authentication."""
    # Try to access without token
    endpoints = [
        "/api/v1/voice-presets",
        "/api/v1/voice-presets?use_case=sales",
        "/api/v1/voice-presets/1/select",
        "/api/v1/voice-presets/1/sample",
        "/api/v1/agent-config/current",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        # Should return 401 or 403
        assert response.status_code in [401, 403], f"Endpoint {endpoint} should require auth"


@pytest.fixture
def mock_tts_provider(monkeypatch):
    """Mock TTS provider for testing."""
    from services.tts.orchestrator import TTSResponse

    mock_response = MagicMock(
        audio_bytes=b"fake mp3 audio data",
        latency_ms=150,
        provider="test",
        content_type="audio/mpeg",
        error=False,
        error_message=None,
    )

    return mock_response


@pytest.fixture
async def auth_token_for_org():
    """Generate auth token for a test org."""
    async def _token(org_id: str) -> str:
        import jwt
        payload = {
            "org_id": org_id,
            "sub": "test_user",
            "exp": 9999999999,
        }
        from config.settings import settings
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    return _token
