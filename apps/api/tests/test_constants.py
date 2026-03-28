"""
Story 1-1: Core Infrastructure Scaffolding
Story 1-2: Multi-layer Hierarchy & Clerk Auth Integration
Story 1-3: Tenant-Isolated Data Persistence with PostgreSQL RLS

Cross-cutting: Error code synchronization verification.

Ensures AUTH_ERROR_CODES and TENANT_ERROR_CODES defined in multiple
locations remain consistent.
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _extract_js_const(file_path: Path, const_name: str) -> dict[str, str]:
    content = file_path.read_text()
    pattern = rf"{const_name}\s*=\s*\{{([^}}]+)\}}"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return {}
    body = match.group(1)
    result = {}
    for m in re.finditer(r"(\w+)\s*:\s*\"([^\"]+)\"", body):
        result[m.group(1)] = m.group(2)
    return result


def _extract_py_dict(file_path: Path, var_name: str) -> dict[str, str]:
    content = file_path.read_text()
    pattern = rf"{var_name}\s*=\s*\{{([^}}]+)\}}"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return {}
    body = match.group(1)
    result = {}
    for m in re.finditer(r"\"(\w+)\"\s*:\s*\"([^\"]+)\"", body):
        result[m.group(1)] = m.group(2)
    return result


class TestAuthErrorCodesSync:
    def test_auth_error_codes_match_across_all_sources(self):
        ts = _extract_js_const(
            _ROOT / "packages" / "constants" / "index.ts", "AUTH_ERROR_CODES"
        )
        mw = _extract_py_dict(
            _ROOT / "apps" / "api" / "middleware" / "auth.py", "AUTH_ERROR_CODES"
        )
        dep = _extract_py_dict(
            _ROOT / "apps" / "api" / "dependencies" / "org_context.py",
            "AUTH_ERROR_CODES",
        )

        assert ts, "Could not extract AUTH_ERROR_CODES from packages/constants"
        assert mw, "Could not extract AUTH_ERROR_CODES from middleware/auth"
        assert dep, "Could not extract AUTH_ERROR_CODES from dependencies/org_context"

        assert ts == mw, (
            f"AUTH_ERROR_CODES mismatch between TS and middleware/auth:\n"
            f"  TS: {ts}\n  MW: {mw}"
        )
        assert ts == dep, (
            f"AUTH_ERROR_CODES mismatch between TS and dependencies/org_context:\n"
            f"  TS: {ts}\n  DEP: {dep}"
        )

    def test_expected_auth_error_keys_present(self):
        ts = _extract_js_const(
            _ROOT / "packages" / "constants" / "index.ts", "AUTH_ERROR_CODES"
        )
        expected_keys = {
            "AUTH_INVALID_TOKEN",
            "AUTH_TOKEN_EXPIRED",
            "AUTH_UNAUTHORIZED",
            "AUTH_FORBIDDEN",
        }
        assert expected_keys == set(ts.keys()), (
            f"Expected keys {expected_keys}, got {set(ts.keys())}"
        )


class TestTenantErrorCodesSync:
    def test_tenant_error_codes_match_frontend(self):
        ts = _extract_js_const(
            _ROOT / "packages" / "constants" / "index.ts", "TENANT_ERROR_CODES"
        )
        assert ts, "Could not extract TENANT_ERROR_CODES from packages/constants"

        expected_keys = {
            "TENANT_CONTEXT_MISSING",
            "TENANT_ACCESS_DENIED",
            "TENANT_INVALID_ORG_ID",
        }
        assert expected_keys == set(ts.keys()), (
            f"Expected keys {expected_keys}, got {set(ts.keys())}"
        )

    def test_tenant_error_code_values_match_keys(self):
        ts = _extract_js_const(
            _ROOT / "packages" / "constants" / "index.ts", "TENANT_ERROR_CODES"
        )
        for key, value in ts.items():
            assert key == value, f"TENANT_ERROR_CODES key {key} != value {value}"
