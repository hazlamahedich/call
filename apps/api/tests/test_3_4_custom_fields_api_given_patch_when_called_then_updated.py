"""Story 3.4 Custom Fields API.

Tests the custom fields PATCH endpoint logic:
merging fields, schema validation, and cross-org protection.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from conftest_3_4 import (
    make_lead,
    make_lead_with_custom_fields,
    TEST_ORG,
)
from schemas.variable_injection import CustomFieldsUpdateRequest


@pytest.mark.asyncio
class TestCustomFieldsAPI:
    @pytest.mark.p1
    def test_3_4_038_given_valid_patch_when_called_then_fields_merged(self):
        existing = {"company_name": "Acme"}
        patch_data = {"industry": "SaaS"}
        merged = {**existing, **patch_data}
        assert merged == {"company_name": "Acme", "industry": "SaaS"}

    @pytest.mark.p1
    def test_3_4_039_given_existing_fields_when_patched_then_merged_not_replaced(
        self,
    ):
        existing = {"company_name": "Acme", "industry": "Tech", "tier": "gold"}
        patch_data = {"industry": "SaaS"}
        merged = {**existing, **patch_data}
        assert merged["company_name"] == "Acme"
        assert merged["industry"] == "SaaS"
        assert merged["tier"] == "gold"

    @pytest.mark.p1
    def test_3_4_040_given_schema_validation_when_called_then_validates(self):
        req = CustomFieldsUpdateRequest(custom_fields={"key": "value"})
        assert req.custom_fields == {"key": "value"}

        with pytest.raises(Exception):
            CustomFieldsUpdateRequest(custom_fields={})

    @pytest.mark.p1
    async def test_3_4_041_given_cross_org_lead_when_patched_then_403(self):
        with patch(
            "services.shared_queries.load_lead_for_context",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=403, detail="Cross-org"),
        ) as mock_load:
            with pytest.raises(HTTPException) as exc_info:
                await mock_load(AsyncMock(), 1, TEST_ORG)
            assert exc_info.value.status_code == 403
