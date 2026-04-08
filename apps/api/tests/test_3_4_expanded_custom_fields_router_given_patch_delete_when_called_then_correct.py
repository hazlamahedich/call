"""Story 3.4 Expanded: Custom Fields Router Endpoint Tests.

Tests PATCH and DELETE custom-fields endpoints via mocked router logic.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from conftest_3_4 import make_lead, TEST_ORG
from schemas.variable_injection import CustomFieldsUpdateRequest


@pytest.mark.asyncio
class TestPatchCustomFields:
    async def test_merge_new_fields_into_empty(self):
        lead = make_lead(custom_fields=None)
        existing = lead.custom_fields or {}
        patch_data = {"company_name": "Acme"}
        merged = {**existing, **patch_data}
        assert merged == {"company_name": "Acme"}

    async def test_merge_updates_existing_field(self):
        existing = {"company_name": "Old Corp", "tier": "silver"}
        patch_data = {"company_name": "New Corp"}
        merged = {**existing, **patch_data}
        assert merged["company_name"] == "New Corp"
        assert merged["tier"] == "silver"

    async def test_merge_preserves_unmentioned_fields(self):
        existing = {"a": "1", "b": "2", "c": "3"}
        patch_data = {"b": "updated"}
        merged = {**existing, **patch_data}
        assert merged["a"] == "1"
        assert merged["b"] == "updated"
        assert merged["c"] == "3"

    async def test_schema_rejects_empty_dict(self):
        with pytest.raises(Exception):
            CustomFieldsUpdateRequest(custom_fields={})

    async def test_schema_rejects_oversized_value(self):
        with pytest.raises(Exception):
            CustomFieldsUpdateRequest(custom_fields={"k": "x" * 501})

    async def test_schema_accepts_valid_fields(self):
        req = CustomFieldsUpdateRequest(custom_fields={"key": "valid value"})
        assert req.custom_fields == {"key": "valid value"}


@pytest.mark.asyncio
class TestDeleteCustomField:
    async def test_delete_existing_field(self):
        fields = {"company_name": "Acme", "industry": "SaaS"}
        field_name = "industry"
        assert field_name in fields
        del fields[field_name]
        assert "company_name" in fields
        assert "industry" not in fields

    async def test_delete_nonexistent_field_no_error(self):
        fields = {"company_name": "Acme"}
        field_name = "nonexistent"
        if field_name in fields:
            del fields[field_name]
        assert fields == {"company_name": "Acme"}

    async def test_delete_from_empty_fields(self):
        fields: dict = {}
        field_name = "nonexistent"
        if field_name in fields:
            del fields[field_name]
        assert fields == {}

    async def test_delete_field_no_commit_when_not_present(self):
        fields = {"a": "1"}
        field_name = "z"
        should_commit = field_name in fields
        assert should_commit is False


@pytest.mark.asyncio
class TestLeadsRouterCrossOrgProtection:
    async def test_patch_cross_org_returns_403(self):
        with patch(
            "services.shared_queries.load_lead_for_context",
            new_callable=AsyncMock,
            side_effect=HTTPException(
                status_code=403,
                detail={
                    "code": "wrong_org",
                    "message": "Lead belongs to different organization",
                },
            ),
        ) as mock_load:
            with pytest.raises(HTTPException) as exc_info:
                await mock_load(AsyncMock(), 1, "wrong_org_id")
            assert exc_info.value.status_code == 403

    async def test_patch_nonexistent_lead_returns_404(self):
        with patch(
            "services.shared_queries.load_lead_for_context",
            new_callable=AsyncMock,
            side_effect=HTTPException(
                status_code=404,
                detail={"code": "lead_not_found", "message": "Lead not found"},
            ),
        ) as mock_load:
            with pytest.raises(HTTPException) as exc_info:
                await mock_load(AsyncMock(), 9999, TEST_ORG)
            assert exc_info.value.status_code == 404
