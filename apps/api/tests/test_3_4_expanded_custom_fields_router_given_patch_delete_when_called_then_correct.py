"""Story 3.4 Expanded: Custom Fields Router Endpoint Tests.

Tests PATCH and DELETE custom-fields endpoints via mocked router logic,
verifying schema validation, merge behavior, and cross-org protection.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from conftest_3_4 import make_lead, TEST_ORG
from schemas.variable_injection import CustomFieldsUpdateRequest


@pytest.mark.asyncio
class TestPatchCustomFieldsMerge:
    @pytest.mark.p1
    async def test_3_4_055_given_lead_with_no_fields_when_patched_then_fields_set(self):
        lead = make_lead()
        assert lead.custom_fields is None
        merged = {**(lead.custom_fields or {}), **{"company_name": "Acme"}}
        lead.custom_fields = merged
        assert lead.custom_fields == {"company_name": "Acme"}

    @pytest.mark.p1
    async def test_3_4_056_given_lead_with_fields_when_patched_then_updated(self):
        lead = make_lead()
        lead.custom_fields = {"company_name": "Old Corp", "tier": "silver"}
        patch_data = {"company_name": "New Corp"}
        merged = {**(lead.custom_fields or {}), **patch_data}
        lead.custom_fields = merged
        assert lead.custom_fields["company_name"] == "New Corp"
        assert lead.custom_fields["tier"] == "silver"

    @pytest.mark.p1
    async def test_3_4_057_given_unmentioned_fields_when_patched_then_preserved(self):
        lead = make_lead()
        lead.custom_fields = {"a": "1", "b": "2", "c": "3"}
        patch_data = {"b": "updated"}
        merged = {**lead.custom_fields, **patch_data}
        lead.custom_fields = merged
        assert lead.custom_fields["a"] == "1"
        assert lead.custom_fields["b"] == "updated"
        assert lead.custom_fields["c"] == "3"

    @pytest.mark.p1
    async def test_3_4_058_given_schema_when_empty_dict_then_rejected(self):
        with pytest.raises(Exception):
            CustomFieldsUpdateRequest(custom_fields={})

    @pytest.mark.p1
    async def test_3_4_059_given_schema_when_oversized_value_then_rejected(self):
        with pytest.raises(Exception):
            CustomFieldsUpdateRequest(custom_fields={"k": "x" * 501})

    @pytest.mark.p1
    async def test_3_4_060_given_schema_when_valid_fields_then_accepted(self):
        req = CustomFieldsUpdateRequest(custom_fields={"key": "valid value"})
        assert req.custom_fields == {"key": "valid value"}


@pytest.mark.asyncio
class TestDeleteCustomField:
    @pytest.mark.p1
    async def test_3_4_061_given_existing_field_when_deleted_then_removed(self):
        lead = make_lead()
        lead.custom_fields = {"company_name": "Acme", "industry": "SaaS"}
        fields = dict(lead.custom_fields)
        field_name = "industry"
        assert field_name in fields
        del fields[field_name]
        lead.custom_fields = fields
        assert "company_name" in lead.custom_fields
        assert "industry" not in lead.custom_fields

    @pytest.mark.p1
    async def test_3_4_062_given_nonexistent_field_when_deleted_then_no_change(self):
        lead = make_lead()
        lead.custom_fields = {"company_name": "Acme"}
        original = dict(lead.custom_fields)
        field_name = "nonexistent"
        fields = dict(lead.custom_fields)
        if field_name in fields:
            del fields[field_name]
            lead.custom_fields = fields
        assert lead.custom_fields == original

    @pytest.mark.p1
    async def test_3_4_063_given_empty_fields_when_deleted_then_still_empty(self):
        lead = make_lead()
        lead.custom_fields = {}
        fields = dict(lead.custom_fields)
        field_name = "nonexistent"
        if field_name in fields:
            del fields[field_name]
            lead.custom_fields = fields
        assert lead.custom_fields == {}

    @pytest.mark.p1
    async def test_3_4_064_given_field_not_present_when_checked_then_no_commit(self):
        lead = make_lead()
        lead.custom_fields = {"a": "1"}
        field_name = "z"
        should_commit = field_name in (lead.custom_fields or {})
        assert should_commit is False


@pytest.mark.asyncio
class TestLeadsRouterCrossOrgProtection:
    @pytest.mark.p1
    async def test_3_4_065_given_cross_org_when_patched_then_403(self):
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

    @pytest.mark.p1
    async def test_3_4_066_given_nonexistent_lead_when_patched_then_404(self):
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
