"""Unit tests for voice preset CRUD operations.

[2.6-BACKEND-PRESETS-001] Test GET presets returns org-scoped presets
[2.6-BACKEND-PRESETS-002] Test GET presets filters by use_case
[2.6-BACKEND-PRESETS-003] Test select preset updates agent
[2.6-BACKEND-PRESETS-004] Test select preset copies preset values to config
[2.6-BACKEND-PRESETS-005] Test tenant isolation (org1 can't see org2 presets)
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.agent import Agent
from models.voice_preset import VoicePreset
from schemas.voice_presets import VoicePresetResponse, VoicePresetSelectResponse


@pytest.mark.asyncio
async def test_get_presets_returns_org_scoped_presets(
    db_session: AsyncSession,
    auth_token_for_org,
    preset_factory,
):
    """[2.6-BACKEND-PRESETS-001] GET /voice-presets returns only presets for tenant's org."""
    # Create presets for two different orgs
    org1_preset = await preset_factory(
        org_id="org1",
        name="Org1 Preset",
        use_case="sales",
    )
    await preset_factory(
        org_id="org2",
        name="Org2 Preset",
        use_case="sales",
    )

    # Get token for org1
    token = await auth_token_for_org("org1")

    # Make request
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    response = client.get(
        "/api/v1/voice-presets",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Should only return org1's presets
    assert data["count"] == 1
    assert data["presets"][0]["name"] == "Org1 Preset"
    assert data["presets"][0]["org_id"] == "org1"


@pytest.mark.asyncio
async def test_get_presets_filters_by_use_case(
    db_session: AsyncSession,
    auth_token_for_org,
    preset_factory,
):
    """[2.6-BACKEND-PRESETS-002] GET /voice-presets?use_case=sales filters correctly."""
    org_id = "test_org"

    # Create presets for different use cases
    await preset_factory(org_id=org_id, name="Sales Preset", use_case="sales")
    await preset_factory(org_id=org_id, name="Support Preset", use_case="support")
    await preset_factory(org_id=org_id, name="Marketing Preset", use_case="marketing")

    token = await auth_token_for_org(org_id)

    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # Request sales presets only
    response = client.get(
        "/api/v1/voice-presets?use_case=sales",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Should only return sales preset
    assert data["count"] == 1
    assert data["presets"][0]["name"] == "Sales Preset"
    assert data["presets"][0]["use_case"] == "sales"


@pytest.mark.asyncio
async def test_select_preset_updates_agent(
    db_session: AsyncSession,
    auth_token_for_org,
    preset_factory,
    agent_factory,
):
    """[2.6-BACKEND-PRESETS-003] POST /voice-presets/{id}/select updates agent config."""
    org_id = "test_org"

    # Create agent and preset
    agent = await agent_factory(org_id=org_id)
    preset = await preset_factory(
        org_id=org_id,
        name="Test Preset",
        speech_speed=1.2,
        stability=0.7,
        temperature=0.8,
    )

    token = await auth_token_for_org(org_id)

    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    response = client.post(
        f"/api/v1/voice-presets/{preset.id}/select",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["preset_id"] == preset.id
    assert "saved successfully" in data["message"]

    # Verify agent was updated
    await db_session.refresh(agent)
    assert agent.preset_id == preset.id
    assert agent.use_advanced_mode is False


@pytest.mark.asyncio
async def test_select_preset_copies_values(
    db_session: AsyncSession,
    auth_token_for_org,
    preset_factory,
    agent_factory,
):
    """[2.6-BACKEND-PRESETS-004] Selecting preset copies TTS values to agent."""
    org_id = "test_org"

    agent = await agent_factory(org_id=org_id)
    preset = await preset_factory(
        org_id=org_id,
        speech_speed=1.3,
        stability=0.6,
        temperature=0.9,
    )

    token = await auth_token_for_org(org_id)

    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    response = client.post(
        f"/api/v1/voice-presets/{preset.id}/select",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200

    # Verify values were copied
    await db_session.refresh(agent)
    assert agent.speech_speed == 1.3
    assert agent.stability == 0.6
    assert agent.temperature == 0.9


@pytest.mark.asyncio
async def test_tenant_isolation_org_cannot_access_other_org_presets(
    db_session: AsyncSession,
    auth_token_for_org,
    preset_factory,
):
    """[2.6-BACKEND-PRESETS-005] Org1 cannot access or select Org2's presets."""
    # Create preset for org2
    org2_preset = await preset_factory(
        org_id="org2",
        name="Org2 Only Preset",
        use_case="sales",
    )

    # Try to access with org1 token
    org1_token = await auth_token_for_org("org1")

    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # Should not see org2's preset in list
    response = client.get(
        "/api/v1/voice-presets",
        headers={"Authorization": f"Bearer {org1_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Org1 should see 0 presets (org2's preset is hidden)
    assert data["count"] == 0

    # Should not be able to select org2's preset directly
    response = client.post(
        f"/api/v1/voice-presets/{org2_preset.id}/select",
        headers={"Authorization": f"Bearer {org1_token}"}
    )

    assert response.status_code == 404
    assert "not found or access denied" in response.json()["detail"]["message"]


@pytest.fixture
async def preset_factory(db_session: AsyncSession):
    """Factory for creating test voice presets."""
    created_presets = []

    async def _create(
        org_id: str = "default",
        name: str = "Test Preset",
        use_case: str = "sales",
        voice_id: str = "test_voice",
        speech_speed: float = 1.0,
        stability: float = 0.8,
        temperature: float = 0.7,
        description: str = "Test description",
        is_active: bool = True,
        sort_order: int = 1,
    ) -> VoicePreset:
        preset = VoicePreset(
            org_id=org_id,
            name=name,
            use_case=use_case,
            voice_id=voice_id,
            speech_speed=speech_speed,
            stability=stability,
            temperature=temperature,
            description=description,
            is_active=is_active,
            sort_order=sort_order,
        )
        db_session.add(preset)
        await db_session.commit()
        await db_session.refresh(preset)
        created_presets.append(preset)
        return preset

    yield _create

    # Cleanup
    for preset in created_presets:
        await db_session.delete(preset)
    await db_session.commit()


@pytest.fixture
async def agent_factory(db_session: AsyncSession):
    """Factory for creating test agents."""
    created_agents = []

    async def _create(
        org_id: str = "test_org",
        name: str = "Test Agent",
    ) -> Agent:
        agent = Agent(
            org_id=org_id,
            name=name,
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)
        created_agents.append(agent)
        return agent

    yield _create

    # Cleanup
    for agent in created_agents:
        await db_session.delete(agent)
    await db_session.commit()


@pytest.mark.asyncio
async def test_save_advanced_config_saves_custom_values(
    db_session: AsyncSession,
    auth_token_for_org,
    agent_factory,
):
    """[2.6-ADVANCED-BACKEND-001] POST /agent-config/advanced saves custom config."""
    org_id = "test_advanced"

    # Create agent
    agent = await agent_factory(org_id=org_id)

    token = await auth_token_for_org(org_id)

    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # Save advanced config
    response = client.post(
        "/api/v1/agent-config/advanced",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "speech_speed": 1.5,
            "stability": 0.6,
            "temperature": 0.9,
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["preset_id"] is None  # No preset for advanced mode
    assert "saved successfully" in data["message"]

    # Verify agent was updated
    await db_session.refresh(agent)
    assert agent.use_advanced_mode is True
    assert agent.preset_id is None
    assert agent.speech_speed == 1.5
    assert agent.stability == 0.6
    assert agent.temperature == 0.9


@pytest.mark.asyncio
async def test_advanced_config_validates_input_ranges(
    db_session: AsyncSession,
    auth_token_for_org,
):
    """[2.6-ADVANCED-BACKEND-002] Advanced config validates value ranges."""
    org_id = "test_validation"
    token = await auth_token_for_org(org_id)

    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # Test invalid speech speed
    response = client.post(
        "/api/v1/agent-config/advanced",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "speech_speed": 3.0,  # Too high
            "stability": 0.8,
            "temperature": 0.7,
        }
    )

    assert response.status_code == 400
    assert "between 0.5 and 2.0" in response.json()["detail"]["message"]

    # Test invalid stability
    response = client.post(
        "/api/v1/agent-config/advanced",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "speech_speed": 1.0,
            "stability": 1.5,  # Too high
            "temperature": 0.7,
        }
    )

    assert response.status_code == 400
    assert "between 0.0 and 1.0" in response.json()["detail"]["message"]


@pytest.fixture
async def auth_token_for_org():
    """Generate auth token for a test org."""
    async def _token(org_id: str) -> str:
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
