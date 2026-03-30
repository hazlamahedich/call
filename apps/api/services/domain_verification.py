import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import dns.asyncresolver
import dns.resolver
import dns.exception

logger = logging.getLogger(__name__)


@dataclass
class DomainVerificationResult:
    verified: bool
    message: str
    instructions: Optional[str] = None


async def verify_cname(domain: str, expected_target: str) -> DomainVerificationResult:
    try:
        resolver = dns.asyncresolver.Resolver()
        resolver.timeout = 10.0
        resolver.lifetime = 15.0
        answers = await resolver.resolve(domain, "CNAME")
        for rdata in answers:
            target_str = str(rdata.target).rstrip(".")
            if target_str == expected_target or target_str.endswith(
                "." + expected_target
            ):
                return DomainVerificationResult(
                    verified=True, message="CNAME verified successfully"
                )
        return DomainVerificationResult(
            verified=False,
            message="CNAME does not point to expected target",
            instructions=f"Add a CNAME record: {domain} → {expected_target}",
        )
    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.exception.DNSException,
    ) as exc:
        logger.info(f"DNS lookup failed for {domain}: {exc}")
        return DomainVerificationResult(
            verified=False,
            message="No CNAME record found",
            instructions=f"Add a CNAME record: {domain} → {expected_target}",
        )
