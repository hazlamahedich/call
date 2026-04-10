"""[4.1-EXP] _normalize_source edge cases and negative paths"""

from __future__ import annotations

import pytest

from services.compliance.dnc import _normalize_source


# ============================================================
# [4.1-EXP-UNIT] _normalize_source known sources
# ============================================================


@pytest.mark.p2
def test_4_1_exp_normalize_national_dnc():
    assert _normalize_source("national_dnc") == "national_dnc"


@pytest.mark.p2
def test_4_1_exp_normalize_state_dnc():
    assert _normalize_source("state_dnc") == "state_dnc"


@pytest.mark.p2
def test_4_1_exp_normalize_tenant_blocklist():
    assert _normalize_source("tenant_blocklist") == "tenant_blocklist"


# ============================================================
# [4.1-EXP-UNIT] _normalize_source keyword matching
# ============================================================


@pytest.mark.p2
def test_4_1_exp_normalize_state_keyword_variants():
    assert _normalize_source("state_level") == "state_dnc"
    assert _normalize_source("StateRegistry") == "state_dnc"
    assert _normalize_source("mystate") == "state_dnc"


@pytest.mark.p2
def test_4_1_exp_normalize_blocklist_keyword_variants():
    assert _normalize_source("internal_blocklist") == "tenant_blocklist"
    assert _normalize_source("BlocklistEntry") == "tenant_blocklist"
    assert _normalize_source("myblocklist") == "tenant_blocklist"


# ============================================================
# [4.1-EXP-UNIT] _normalize_source unknown / edge cases
# ============================================================


@pytest.mark.p2
def test_4_1_exp_normalize_federal_dnc_defaults_national():
    assert _normalize_source("federal_dnc") == "national_dnc"


@pytest.mark.p2
def test_4_1_exp_normalize_company_blocklist_defaults_national():
    assert _normalize_source("company_blocklist") == "tenant_blocklist"


@pytest.mark.p2
def test_4_1_exp_normalize_empty_string():
    assert _normalize_source("") == "national_dnc"


@pytest.mark.p2
def test_4_1_exp_normalize_dnc_com():
    assert _normalize_source("dnc_com") == "national_dnc"


@pytest.mark.p2
def test_4_1_exp_normalize_mock_provider():
    assert _normalize_source("mock_provider") == "national_dnc"


@pytest.mark.p2
def test_4_1_exp_normalize_case_insensitive_state():
    assert _normalize_source("STATE_DNC") == "state_dnc"


@pytest.mark.p2
def test_4_1_exp_normalize_case_insensitive_blocklist():
    assert _normalize_source("BLOCKLIST_auto") == "tenant_blocklist"


@pytest.mark.p2
def test_4_1_exp_normalize_numeric_string():
    assert _normalize_source("12345") == "national_dnc"


@pytest.mark.p2
def test_4_1_exp_normalize_cache_source():
    assert _normalize_source("cache") == "national_dnc"


@pytest.mark.p2
def test_4_1_exp_normalize_circuit_breaker_source():
    assert _normalize_source("circuit_breaker") == "national_dnc"


@pytest.mark.p2
def test_4_1_exp_normalize_provider_error_source():
    assert _normalize_source("provider_error") == "national_dnc"
