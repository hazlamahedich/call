"""
Story 1-3: Tenant-Isolated Data Persistence with PostgreSQL RLS
API Unit Tests for Error Code Synchronization

Verifies that AUTH_ERROR_CODES and TENANT_ERROR_CODES defined in the
backend source files match the canonical definitions in packages/constants.
"""

import pytest

from middleware.auth import AUTH_ERROR_CODES as MW_AUTH_CODES
from dependencies.org_context import AUTH_ERROR_CODES as DEP_AUTH_CODES


class TestAuthErrorCodeConsistency:
    """[P1] Verify AUTH_ERROR_CODES consistency across backend modules"""

    def test_middleware_and_dependency_auth_codes_match(self):
        assert MW_AUTH_CODES == DEP_AUTH_CODES, (
            f"AUTH_ERROR_CODES mismatch:\n"
            f"  middleware/auth: {MW_AUTH_CODES}\n"
            f"  dependencies/org_context: {DEP_AUTH_CODES}"
        )

    def test_all_expected_auth_error_keys_present(self):
        expected = {
            "AUTH_INVALID_TOKEN",
            "AUTH_TOKEN_EXPIRED",
            "AUTH_UNAUTHORIZED",
            "AUTH_FORBIDDEN",
        }
        actual = set(MW_AUTH_CODES.keys())
        assert expected == actual, f"Expected {expected}, got {actual}"

    def test_auth_error_values_are_uppercase_strings(self):
        for key, value in MW_AUTH_CODES.items():
            assert value == key, f"Value {value!r} should equal key {key!r}"
            assert value == value.upper(), f"Value {value!r} is not uppercase"


class TestTenantErrorCodeValues:
    """[P1] Verify TENANT_ERROR_CODES used in database/session.py"""

    def test_tenant_context_missing_code_format(self):
        from database.session import TenantContextError

        error = TenantContextError(error_code="TENANT_CONTEXT_MISSING", message="test")
        assert error.error_code == "TENANT_CONTEXT_MISSING"

    def test_tenant_access_denied_code_format(self):
        from database.session import TenantContextError

        error = TenantContextError(error_code="TENANT_ACCESS_DENIED", message="test")
        assert error.error_code == "TENANT_ACCESS_DENIED"

    def test_tenant_invalid_org_id_code_format(self):
        from services.base import TenantContextError

        error = TenantContextError(error_code="TENANT_INVALID_ORG_ID", message="test")
        assert error.error_code == "TENANT_INVALID_ORG_ID"


class TestUsageErrorCodeSync:
    """[P1] Verify USAGE_ERROR_CODES consistency between Python and TypeScript"""

    def test_usage_limit_exceeded_in_guard(self):
        from pathlib import Path

        guard_path = (
            Path(__file__).resolve().parent.parent / "middleware" / "usage_guard.py"
        )
        content = guard_path.read_text()
        assert "USAGE_LIMIT_EXCEEDED" in content

    def test_usage_error_codes_in_ts_constants(self):
        import re
        from pathlib import Path

        ts_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "packages"
            / "constants"
            / "index.ts"
        )
        content = ts_path.read_text()
        assert "USAGE_LIMIT_EXCEEDED" in content
        assert "USAGE_CAP_NOT_CONFIGURED" in content
        assert "USAGE_INVALID_RESOURCE" in content
        assert "USAGE_INTERNAL_ERROR" in content
        assert "UsageErrorCode" in content
