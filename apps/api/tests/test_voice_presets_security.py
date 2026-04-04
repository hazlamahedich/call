"""P0 Security test: Tenant isolation enforcement.

[2.6-SECURITY-TENANT-ISOLATION-001] Test prevents preset_id tampering for privilege escalation
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.voice_preset import VoicePreset
from models.agent import Agent


@pytest.mark.asyncio
async def test_tenant_isolation_preset_access_control(
    db_session: AsyncSession,
    client,
    auth_token_for_org,
):
    """[2.6-SECURITY-TENANT-ISOLATION-001] Org1 cannot access Org2's presets via any means.

    This is a CRITICAL security test to prevent privilege escalation via preset_id tampering.
    """
    # Create two orgs with different IDs
    org1_id = "org1_tenant"
    org2_id = "org2_tenant"

    # Create preset for org2
    org2_preset = VoicePreset(
        org_id=org2_id,
        name="Org2 Secret Preset",
        use_case="sales",
        voice_id="org2_voice",
        speech_speed=1.5,
        stability=0.5,
        temperature=0.9,
        description="This should only be accessible to org2",
        is_active=True,
        sort_order=1,
    )
    db_session.add(org2_preset)
    await db_session.commit()
    await db_session.refresh(org2_preset)

    # Get token for org1 (attacker)
    org1_token = await auth_token_for_org(org1_id)

    # ATTACK VECTOR 1: Try to list all presets (should not see org2's preset)
    response = client.get(
        "/api/v1/voice-presets",
        headers={"Authorization": f"Bearer {org1_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Org1 should see 0 presets (org2's preset is filtered by org_id)
    assert data["count"] == 0
    assert len(data["presets"]) == 0

    # ATTACK VECTOR 2: Try to access org2's preset directly by ID
    response = client.get(
        f"/api/v1/voice-presets/{org2_preset.id}/sample",
        headers={"Authorization": f"Bearer {org1_token}"}
    )

    # Should be denied - 404 Not Found (security through obscurity)
    # OR 403 Forbidden (explicit denial)
    assert response.status_code in [403, 404]
    if response.status_code == 404:
        assert "not found" in response.json()["detail"]["message"].lower()
    else:
        assert "access denied" in response.json()["detail"]["message"].lower() or "forbidden" in response.json()["detail"]["message"].lower()

    # ATTACK VECTOR 3: Try to select org2's preset
    response = client.post(
        f"/api/v1/voice-presets/{org2_preset.id}/select",
        headers={"Authorization": f"Bearer {org1_token}"}
    )

    # Should be denied
    assert response.status_code in [403, 404]
    if response.status_code == 404:
        assert "not found" in response.json()["detail"]["message"].lower()
    else:
        assert "access denied" in response.json()["detail"]["message"].lower() or "forbidden" in response.json()["detail"]["message"].lower()

    # Verify org1's agent was NOT updated with org2's preset
    response = client.get(
        "/api/v1/agent-config/current",
        headers={"Authorization": f"Bearer {org1_token}"}
    )

    assert response.status_code == 200
    agent_config = response.json()

    # Should not have org2's preset selected
    assert agent_config.get("preset_id") != org2_preset.id
    assert agent_config.get("preset_id") is None

    # Cleanup
    await db_session.delete(org2_preset)
    await db_session.commit()


@pytest.mark.asyncio
async def test_preset_id_tampering_prevents_data_leakage(
    db_session: AsyncSession,
    client,
    auth_token_for_org,
):
    """Test that preset_id enumeration doesn't leak data about other orgs."""
    # Create preset for org2
    org2_preset = VoicePreset(
        org_id="org2_secret",
        name="Org2 Preset",
        use_case="sales",
        voice_id="voice2",
        speech_speed=1.0,
        stability=0.8,
        temperature=0.7,
        description="Secret preset",
        is_active=True,
        sort_order=1,
    )
    db_session.add(org2_preset)
    await db_session.commit()

    # Attacker from org1 tries to enumerate preset IDs
    org1_token = await auth_token_for_org("org1_attacker")

    # Try to access by ID (should not reveal if preset exists)
    response = client.get(
        f"/api/v1/voice-presets/{org2_preset.id}/sample",
        headers={"Authorization": f"Bearer {org1_token}"}
    )

    # Should return generic 404, not 403 (to prevent ID enumeration)
    assert response.status_code == 404

    # Response should NOT reveal that a preset with this ID exists for another org
    error_msg = response.json()["detail"]["message"].lower()
    assert "not found" in error_msg or "access denied" in error_msg
    # Should NOT contain org2's name or details
    assert "org2" not in error_msg
    assert "secret" not in error_msg

    # Cleanup
    await db_session.delete(org2_preset)
    await db_session.commit()


@pytest.mark.asyncio
async def test_cross_tenant_preset_selection_isolation(
    db_session: AsyncSession,
    client,
    auth_token_for_org,
):
    """Test that preset selection doesn't affect other orgs' agents."""
    org1_id = "org1_isolated"
    org2_id = "org2_isolated"

    # Create preset for org1
    org1_preset = VoicePreset(
        org_id=org1_id,
        name="Org1 Preset",
        use_case="sales",
        voice_id="voice1",
        speech_speed=1.2,
        stability=0.7,
        temperature=0.8,
        description="Org1 only",
        is_active=True,
        sort_order=1,
    )
    db_session.add(org1_preset)
    await db_session.commit()

    # Create preset for org2
    org2_preset = VoicePreset(
        org_id=org2_id,
        name="Org2 Preset",
        use_case="sales",
        voice_id="voice2",
        speech_speed=1.0,
        stability=0.9,
        temperature=0.6,
        description="Org2 only",
        is_active=True,
        sort_order=1,
    )
    db_session.add(org2_preset)
    await db_session.commit()

    # Org1 selects their preset
    org1_token = await auth_token_for_org(org1_id)
    response = client.post(
        f"/api/v1/voice-presets/{org1_preset.id}/select",
        headers={"Authorization": f"Bearer {org1_token}"}
    )
    assert response.status_code == 200

    # Org2 selects their preset
    org2_token = await auth_token_for_org(org2_id)
    response = client.post(
        f"/api/v1/voice-presets/{org2_preset.id}/select",
        headers={"Authorization": f"Bearer {org2_token}"}
    )
    assert response.status_code == 200

    # Verify org1's agent has org1's preset
    response = client.get(
        "/api/v1/agent-config/current",
        headers={"Authorization": f"Bearer {org1_token}"}
    )
    assert response.status_code == 200
    org1_config = response.json()
    assert org1_config["preset_id"] == org1_preset.id

    # Verify org2's agent has org2's preset
    response = client.get(
        "/api/v1/agent-config/current",
        headers={"Authorization": f"Bearer {org2_token}"}
    )
    assert response.status_code == 200
    org2_config = response.json()
    assert org2_config["preset_id"] == org2_preset.id

    # Verify configs are different (isolation working)
    assert org1_config["preset_id"] != org2_config["preset_id"]

    # Cleanup
    await db_session.delete(org1_preset)
    await db_session.delete(org2_preset)
    await db_session.commit()


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
