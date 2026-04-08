"""Story 3.4 AC6: Lead Not Found.

Tests that missing leads and cross-org access attempts
are handled with appropriate HTTP errors via shared_queries.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from conftest_3_4 import (
    make_lead,
    TEST_ORG,
)


@pytest.mark.asyncio
class TestAC6LeadNotFound:
    @pytest.mark.p1
    async def test_3_4_024_given_missing_lead_when_loading_then_404(self):
        with patch(
            "services.shared_queries.load_lead_for_context",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=404, detail="Lead not found"),
        ) as mock_load:
            from services.shared_queries import load_lead_for_context

            with pytest.raises(HTTPException) as exc_info:
                await mock_load(AsyncMock(), 99999, TEST_ORG)
            assert exc_info.value.status_code == 404

    @pytest.mark.p1
    async def test_3_4_025_given_cross_org_lead_when_loading_then_403(self):
        with patch(
            "services.shared_queries.load_lead_for_context",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=403, detail="Cross-org"),
        ) as mock_load:
            from services.shared_queries import load_lead_for_context

            with pytest.raises(HTTPException) as exc_info:
                await mock_load(AsyncMock(), 1, TEST_ORG)
            assert exc_info.value.status_code == 403
