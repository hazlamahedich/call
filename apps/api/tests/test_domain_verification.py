"""
Story 1-5: White-labeled Admin Portal & Custom Branding
Extended Unit Tests for Domain Verification Service

Test ID Format: 1.5-API-DNS-XXX
Priority: P0 (Critical) | P1 (High) | P2 (Medium)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import dns.resolver
import dns.exception

from services.domain_verification import verify_cname, DomainVerificationResult


class TestVerifyCnameEdgeCases:
    """[1.5-API-DNS-001..010] Extended DNS verification tests"""

    @pytest.mark.asyncio
    async def test_timeout_returns_failure(self):
        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_cls:
            mock_resolver = MagicMock()
            mock_cls.return_value = mock_resolver
            mock_resolver.resolve = AsyncMock(side_effect=dns.exception.Timeout())

            result = await verify_cname("slow.example.com", "cname.call.app")

            assert result.verified is False
            assert "No CNAME" in result.message
            assert result.instructions is not None

    @pytest.mark.asyncio
    async def test_generic_dns_exception_returns_failure(self):
        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_cls:
            mock_resolver = MagicMock()
            mock_cls.return_value = mock_resolver
            mock_resolver.resolve = AsyncMock(side_effect=dns.exception.DNSException())

            result = await verify_cname("error.example.com", "cname.call.app")

            assert result.verified is False
            assert result.instructions is not None

    @pytest.mark.asyncio
    async def test_subdomain_target_match(self):
        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_cls:
            mock_resolver = MagicMock()
            mock_cls.return_value = mock_resolver
            mock_rdata = MagicMock()
            mock_rdata.target = "sub.cname.call.app."
            mock_resolver.resolve = AsyncMock(return_value=[mock_rdata])

            result = await verify_cname("custom.example.com", "cname.call.app")

            assert result.verified is True
            assert "verified" in result.message.lower()

    @pytest.mark.asyncio
    async def test_empty_cname_answers(self):
        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_cls:
            mock_resolver = MagicMock()
            mock_cls.return_value = mock_resolver
            mock_resolver.resolve = AsyncMock(return_value=[])

            result = await verify_cname("empty.example.com", "cname.call.app")

            assert result.verified is False
            assert "does not point" in result.message.lower()

    @pytest.mark.asyncio
    async def test_resolver_timeout_config(self):
        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_cls:
            mock_resolver = MagicMock()
            mock_cls.return_value = mock_resolver
            mock_resolver.resolve = AsyncMock(side_effect=dns.resolver.NXDOMAIN())

            await verify_cname("test.example.com", "cname.call.app")

            assert mock_resolver.timeout == 10.0
            assert mock_resolver.lifetime == 15.0

    @pytest.mark.asyncio
    async def test_target_with_trailing_dot(self):
        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_cls:
            mock_resolver = MagicMock()
            mock_cls.return_value = mock_resolver
            mock_rdata = MagicMock()
            mock_rdata.target = "cname.call.app."
            mock_resolver.resolve = AsyncMock(return_value=[mock_rdata])

            result = await verify_cname("custom.example.com", "cname.call.app")

            assert result.verified is True

    @pytest.mark.asyncio
    async def test_no_answer_exception(self):
        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_cls:
            mock_resolver = MagicMock()
            mock_cls.return_value = mock_resolver
            mock_resolver.resolve = AsyncMock(side_effect=dns.resolver.NoAnswer())

            result = await verify_cname("noanswer.example.com", "cname.call.app")

            assert result.verified is False
            assert "No CNAME" in result.message

    @pytest.mark.asyncio
    async def test_nxdomain_exception(self):
        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_cls:
            mock_resolver = MagicMock()
            mock_cls.return_value = mock_resolver
            mock_resolver.resolve = AsyncMock(side_effect=dns.resolver.NXDOMAIN())

            result = await verify_cname("missing.example.com", "cname.call.app")

            assert result.verified is False
            assert "No CNAME" in result.message
            assert "Add a CNAME record" in result.instructions

    @pytest.mark.asyncio
    async def test_wrong_target_returns_instructions(self):
        with patch(
            "services.domain_verification.dns.asyncresolver.Resolver"
        ) as mock_cls:
            mock_resolver = MagicMock()
            mock_cls.return_value = mock_resolver
            mock_rdata = MagicMock()
            mock_rdata.target = "other.target.com."
            mock_resolver.resolve = AsyncMock(return_value=[mock_rdata])

            result = await verify_cname("custom.example.com", "cname.call.app")

            assert result.verified is False
            assert result.instructions is not None
            assert "cname.call.app" in result.instructions


class TestDomainVerificationResultDataclass:
    """[1.5-API-DNS-011..013] DomainVerificationResult dataclass tests"""

    def test_result_with_required_fields(self):
        result = DomainVerificationResult(
            verified=True, message="CNAME verified successfully"
        )
        assert result.verified is True
        assert result.message == "CNAME verified successfully"
        assert result.instructions is None

    def test_result_with_instructions(self):
        result = DomainVerificationResult(
            verified=False,
            message="No CNAME record found",
            instructions="Add a CNAME record: example.com → cname.call.app",
        )
        assert result.instructions is not None
        assert "CNAME" in result.instructions

    def test_result_fields_are_immutable_by_convention(self):
        result = DomainVerificationResult(verified=True, message="verified")
        assert hasattr(result, "verified")
        assert hasattr(result, "message")
        assert hasattr(result, "instructions")
