"""
Story 1-3: Tenant-Isolated Data Persistence with PostgreSQL RLS
API Unit Tests for TenantService Edge Cases

Test ID Format: 1.3-API-XXX
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from models.lead import Lead
from services.base import TenantService
from database.session import TenantContextError


class TestTenantServiceUpdateEdgeCases:
    """[P1] Edge case tests for TenantService.update()"""

    def test_update_with_none_id_raises_error(self):
        service = TenantService[Lead](Lead)
        lead = Lead(name="Test", email="test@example.com")
        assert lead.id is None

        import asyncio

        with pytest.raises(TenantContextError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                service.update(MagicMock(), lead)
            )
        assert exc_info.value.error_code == "TENANT_INVALID_ORG_ID"


class TestTenantServiceCreateEdgeCases:
    """[P1] Edge case tests for TenantService.create()"""

    @pytest.mark.asyncio
    async def test_create_with_no_tenant_context_raises_error(self):
        service = TenantService[Lead](Lead)

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(scalar=MagicMock(return_value=""))

        lead = Lead(name="No Context", email="noctx@example.com")

        with pytest.raises(TenantContextError) as exc_info:
            await service.create(mock_session, lead)

        assert exc_info.value.error_code == "TENANT_CONTEXT_MISSING"


class TestTenantServiceRowToInstance:
    """[P2] Tests for _row_to_instance edge cases"""

    def test_row_to_instance_with_all_fields(self):
        from datetime import datetime

        service = TenantService[Lead](Lead)

        row = (
            1,
            "org_123",
            "Test Lead",
            "test@example.com",
            None,
            "new",
            datetime.now(),
            datetime.now(),
            False,
        )

        instance = service._row_to_instance(row)
        assert instance.id == 1
        assert instance.org_id == "org_123"
        assert instance.name == "Test Lead"
        assert instance.email == "test@example.com"

    def test_row_to_instance_with_short_row(self):
        service = TenantService[Lead](Lead)

        row = (1, "org_123", "Test Lead", "test@example.com")

        instance = service._row_to_instance(row)
        assert instance.id == 1
        assert instance.name == "Test Lead"
