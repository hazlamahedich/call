from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from .exceptions import ComplianceBlockError

_E164_PATTERN = re.compile(r"^\+\d{7,15}$")


def validate_e164(phone_number: str) -> str:
    if not phone_number or not isinstance(phone_number, str):
        raise ComplianceBlockError(
            code="DNC_INVALID_PHONE_FORMAT",
            phone_number=str(phone_number) if phone_number else "",
            source="validation",
        )
    cleaned = phone_number.strip()
    if not _E164_PATTERN.match(cleaned):
        raise ComplianceBlockError(
            code="DNC_INVALID_PHONE_FORMAT",
            phone_number=phone_number,
            source="validation",
        )
    return cleaned


@dataclass
class DncCheckResult:
    phone_number: str
    is_blocked: bool = False
    source: str = ""
    result: str = "clear"
    raw_response: Optional[dict] = None
    response_time_ms: int = 0


@dataclass
class DncScrubSummary:
    total: int = 0
    blocked: int = 0
    unchecked: int = 0
    sources: dict[str, int] = field(
        default_factory=lambda: {
            "national_dnc": 0,
            "state_dnc": 0,
            "tenant_blocklist": 0,
        }
    )


class DncProvider(ABC):
    @abstractmethod
    async def lookup(self, phone_number: str) -> DncCheckResult:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass
