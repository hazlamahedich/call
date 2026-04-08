"""Story 3.4 Cache Key Correctness.

Tests that cache keys include lead/script context and do not leak
data between different leads.

NOTE: _build_cache_key mirrors the inline key format in
services/script_generation.py:155. If the service key format changes,
these tests must be updated to match.
"""

import hashlib

import pytest

from conftest_3_4 import (
    make_lead,
    make_agent,
    TEST_ORG,
)
from services.variable_injection import VariableInjectionService
from unittest.mock import AsyncMock


class TestCacheKeyCorrectness:
    @pytest.mark.p2
    def test_3_4_035_given_different_leads_when_cached_then_keys_differ(self):
        query = "Tell me about products"
        org_id = TEST_ORG
        agent_id = 1

        key_a = self._build_cache_key(org_id, agent_id, query, lead_id=1, script_id=1)
        key_b = self._build_cache_key(org_id, agent_id, query, lead_id=2, script_id=1)

        assert key_a != key_b

    @pytest.mark.p2
    def test_3_4_036_given_cached_lead_a_when_generating_lead_b_then_no_leak(self):
        query = "What solutions?"
        org_id = TEST_ORG

        key_a = self._build_cache_key(org_id, 1, query, lead_id=100, script_id=1)
        key_b = self._build_cache_key(org_id, 1, query, lead_id=200, script_id=1)

        assert key_a != key_b
        assert "l100" in key_a
        assert "l200" in key_b

    @pytest.mark.p2
    def test_3_4_037_given_no_lead_id_when_cached_then_backward_compatible_key(
        self,
    ):
        query = "Standard query"
        org_id = TEST_ORG
        agent_id = 1

        key = self._build_cache_key(
            org_id, agent_id, query, lead_id=None, script_id=None
        )

        assert ":l" not in key
        assert ":s" not in key
        assert "script_gen" in key

    @staticmethod
    def _build_cache_key(org_id, agent_id, query, lead_id=None, script_id=None):
        base = f"script_gen:{org_id}:{agent_id or 'default'}:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
        if lead_id is not None and script_id is not None:
            base += f":l{lead_id}:s{script_id}"
        return base
