from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

_E164_PATTERN = re.compile(r"^\+\d{7,15}$")


class InvalidPhoneFormatError(ValueError):
    def __init__(self, phone_number: str, message: str = ""):
        self.phone_number = phone_number
        super().__init__(
            message
            or f"Phone number must be in E.164 format (+{{country_code}}{{number}}), got: {phone_number!r}"
        )


def validate_e164(phone_number: str) -> str:
    if not phone_number or not isinstance(phone_number, str):
        raise InvalidPhoneFormatError(
            phone_number or "",
            "Phone number is required and must be a string",
        )
    cleaned = phone_number.strip()
    if not _E164_PATTERN.match(cleaned):
        raise InvalidPhoneFormatError(phone_number)
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
    skipped: int = 0
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
