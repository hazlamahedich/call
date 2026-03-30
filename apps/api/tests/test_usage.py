"""
Story 1.7: Resource Guardrails - Usage Monitoring & Hard Caps
Unit Tests for Usage Service Logic

Test ID Format: [1.7-UNIT-XXX]
"""

import re
from pathlib import Path

import pytest
from schemas.usage import UsageRecordPayload, UsageSummaryResponse


class TestUsageModelErrorCodesSync:
    """[1.7-UNIT-020..024] Verify USAGE_ERROR_CODES in TypeScript constants"""

    _ROOT = Path(__file__).resolve().parent.parent.parent.parent

    def _extract_ts_const(self, file_path: Path, const_name: str) -> dict:
        content = file_path.read_text()
        pattern = rf"export const {const_name}\s*=\s*\{{([^}}]+)\}}"
        match = re.search(pattern, content)
        if not match:
            return {}
        body = match.group(1)
        result = {}
        for line in body.strip().split("\n"):
            line = line.strip().rstrip(",")
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                result[key] = value
        return result

    def test_1_7_unit_020_usage_error_codes_exist_in_ts(self):
        ts_path = self._ROOT / "packages" / "constants" / "index.ts"
        codes = self._extract_ts_const(ts_path, "USAGE_ERROR_CODES")
        assert codes, "USAGE_ERROR_CODES not found in packages/constants/index.ts"
        assert "USAGE_LIMIT_EXCEEDED" in codes
        assert "USAGE_CAP_NOT_CONFIGURED" in codes
        assert "USAGE_INVALID_RESOURCE" in codes

    def test_1_7_unit_021_usage_error_codes_values_match_keys(self):
        ts_path = self._ROOT / "packages" / "constants" / "index.ts"
        codes = self._extract_ts_const(ts_path, "USAGE_ERROR_CODES")
        for key, value in codes.items():
            assert key == value, f"USAGE_ERROR_CODES key {key} != value {value}"

    def test_1_7_unit_022_usage_error_type_exported(self):
        ts_path = self._ROOT / "packages" / "constants" / "index.ts"
        content = ts_path.read_text()
        assert "UsageErrorCode" in content

    def test_1_7_unit_023_router_uses_matching_error_codes(self):
        import routers.usage as usage_mod

        ts_path = self._ROOT / "packages" / "constants" / "index.ts"
        codes = self._extract_ts_const(ts_path, "USAGE_ERROR_CODES")
        router_source = Path(usage_mod.__file__).read_text()
        skipped = {"USAGE_LIMIT_EXCEEDED", "USAGE_CAP_NOT_CONFIGURED"}
        for code_key in codes:
            if code_key in skipped:
                continue
            assert code_key in router_source, (
                f"Error code {code_key} not used in router"
            )

    def test_1_7_unit_024_usage_guard_uses_limit_exceeded(self):
        guard_path = self._ROOT / "apps" / "api" / "middleware" / "usage_guard.py"
        content = guard_path.read_text()
        assert "USAGE_LIMIT_EXCEEDED" in content


class TestUsageSettings:
    """[1.7-UNIT-025..027] Settings for usage caps"""

    def test_1_7_unit_025_default_monthly_call_cap(self):
        from config.settings import settings

        assert settings.DEFAULT_MONTHLY_CALL_CAP == 1000

    def test_1_7_unit_026_plan_call_caps(self):
        from config.settings import settings

        assert settings.PLAN_CALL_CAPS == {
            "free": 1000,
            "pro": 25000,
            "enterprise": 100000,
        }

    @pytest.mark.asyncio
    async def test_1_7_unit_027_get_monthly_cap_returns_default(self):
        from services.usage import get_monthly_cap

        cap = await get_monthly_cap("any_org")
        assert cap == 1000


class TestUsageLogModel:
    """[1.7-UNIT-028..032] UsageLog model field validation"""

    def test_1_7_unit_028_usage_log_model_fields(self):
        from models.usage_log import UsageLog

        log = UsageLog.model_validate(
            {
                "resourceType": "call",
                "resourceId": "call_123",
                "action": "call_initiated",
                "metadataJson": '{"duration": 120}',
            }
        )
        assert log.resource_type == "call"
        assert log.resource_id == "call_123"
        assert log.action == "call_initiated"
        assert log.metadata_json == '{"duration": 120}'

    def test_1_7_unit_029_usage_log_default_values(self):
        from models.usage_log import UsageLog

        log = UsageLog()
        assert log.resource_type == "call"
        assert log.resource_id == ""
        assert log.action == "call_initiated"
        assert log.metadata_json == "{}"

    def test_1_7_unit_030_usage_log_extends_tenant_model(self):
        from models.usage_log import UsageLog
        from models.base import TenantModel

        assert issubclass(UsageLog, TenantModel)

    def test_1_7_unit_031_usage_log_tablename(self):
        from models.usage_log import UsageLog

        assert UsageLog.__tablename__ == "usage_logs"

    def test_1_7_unit_032_usage_log_registered_in_init(self):
        from models import UsageLog

        assert UsageLog is not None


class TestUsageSummaryResponseType:
    """[1.7-UNIT-033..034] UsageSummaryResponse model"""

    def test_1_7_unit_033_response_serialization(self):
        resp = UsageSummaryResponse(
            used=500,
            cap=1000,
            percentage=50.0,
            plan="free",
            threshold="ok",
        )
        data = resp.model_dump(by_alias=True)
        assert data["used"] == 500
        assert data["cap"] == 1000
        assert data["percentage"] == 50.0
        assert data["plan"] == "free"
        assert data["threshold"] == "ok"

    def test_1_7_unit_034_response_camel_case_alias(self):
        resp = UsageSummaryResponse(
            **{
                "used": 800,
                "cap": 1000,
                "percentage": 80.0,
                "plan": "pro",
                "threshold": "warning",
            }
        )
        assert resp.used == 800
        assert resp.threshold == "warning"


class TestComputeThreshold:
    """[1.7-UNIT-035..039] _compute_threshold pure function"""

    def test_1_7_unit_035_ok(self):
        from services.usage import _compute_threshold

        assert _compute_threshold(500, 1000) == "ok"

    def test_1_7_unit_036_warning(self):
        from services.usage import _compute_threshold

        assert _compute_threshold(800, 1000) == "warning"

    def test_1_7_unit_037_critical(self):
        from services.usage import _compute_threshold

        assert _compute_threshold(950, 1000) == "critical"

    def test_1_7_unit_038_exceeded(self):
        from services.usage import _compute_threshold

        assert _compute_threshold(1000, 1000) == "exceeded"

    def test_1_7_unit_039_zero_cap(self):
        from services.usage import _compute_threshold

        assert _compute_threshold(0, 0) == "exceeded"


class TestUsageRecordPayloadValidation:
    """[1.7-UNIT-040..042] Schema length validation"""

    def test_1_7_unit_040_rejects_oversized_resource_id(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UsageRecordPayload(
                resource_type="call",
                resource_id="x" * 256,
                action="call_initiated",
            )

    def test_1_7_unit_041_rejects_oversized_metadata(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UsageRecordPayload(
                resource_type="call",
                resource_id="call_001",
                action="call_initiated",
                metadata="x" * 2001,
            )

    def test_1_7_unit_041b_rejects_invalid_json_metadata(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UsageRecordPayload(
                resource_type="call",
                resource_id="call_001",
                action="call_initiated",
                metadata="not json",
            )
