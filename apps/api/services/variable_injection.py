"""Variable injection service for hyper-personalized script rendering.

Parses {{variable_name}} and {{variable_name:fallback}} templates,
resolves values from lead data, system variables, and custom fields,
with prompt injection defense via sanitization.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings

logger = logging.getLogger(__name__)

VARIABLE_PATTERN = re.compile(r"(?<!\$)\{\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([^}]+))?\}\}")
# Note: The capture group [a-zA-Z_][a-zA-Z0-9_]* inherently rejects whitespace,
# so {{ lead_name }} (with spaces inside braces) is NOT matched — left as literal text.
# The negative lookbehind (?<!\$) prevents matching ${{price}} (only {{...}} syntax).

INJECTION_PATTERNS = [
    re.compile(r"(?i)(ignore\s+(all\s+)?previous\s+instructions)"),
    re.compile(r"(?i)(system\s*prompt|system\s*message)"),
    re.compile(r"(?i)(you\s+are\s+now|act\s+as\s+if)"),
    re.compile(r"(?i)(\<\/?system\>|\<\/?instruction\>)"),
]

SYSTEM_VARIABLES = {
    "current_date": lambda: date.today().isoformat(),
    "current_time": lambda: datetime.now().strftime("%I:%M %p"),
    "current_datetime": lambda: datetime.now().isoformat(),
    "agent_name": None,
}

LEAD_STANDARD_FIELDS = {
    "lead_name": "name",
    "lead_email": "email",
    "lead_phone": "phone",
    "lead_status": "status",
}

FALLBACK_BY_TYPE = {
    "name": "there",
    "company": "your company",
    "date": "recently",
    "email": "Not Available",
    "phone": "Not Available",
}

VARIABLE_TYPE_PATTERNS = {
    "name": re.compile(r"(name|first|last)", re.IGNORECASE),
    "company": re.compile(r"(company|org|business|employer)", re.IGNORECASE),
    "date": re.compile(r"(date|time|when|last_|recent)", re.IGNORECASE),
    "email": re.compile(r"email", re.IGNORECASE),
    "phone": re.compile(r"(phone|tel|mobile)", re.IGNORECASE),
}


def classify_source(name: str) -> str:
    normalized = name.lower().strip()
    if normalized in LEAD_STANDARD_FIELDS:
        return "lead"
    if normalized in SYSTEM_VARIABLES:
        return "system"
    return "custom"


@dataclass
class VariableInfo:
    name: str
    fallback: Optional[str]
    source_type: str
    raw_match: str


@dataclass
class RenderResult:
    rendered_text: str
    resolved_variables: dict[str, str] = field(default_factory=dict)
    unresolved_variables: list[str] = field(default_factory=list)
    was_rendered: bool = False


class VariableInjectionService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def render_template(
        self,
        template: str,
        lead,
        agent=None,
        custom_fallbacks: dict[str, str] | None = None,
    ) -> RenderResult:
        variables = self.extract_variables(template)
        if not variables:
            return RenderResult(
                rendered_text=template,
                resolved_variables={},
                unresolved_variables=[],
                was_rendered=False,
            )

        resolved: dict[str, str] = {}
        unresolved: list[str] = []

        resolution_map: dict[str, str] = {}
        for var in variables:
            normalized = var.name.lower()
            if normalized not in resolution_map:
                value, used_fallback = self._resolve(
                    var_name=var.name,
                    fallback=var.fallback,
                    lead=lead,
                    agent=agent,
                    custom_fallbacks=custom_fallbacks,
                )
                resolution_map[normalized] = value
                resolved[var.name] = value

                if used_fallback:
                    unresolved.append(var.name)

        def _replace_cb(m: re.Match) -> str:
            name = m.group(1)
            normalized = name.lower()
            return resolution_map.get(normalized, m.group(0))

        rendered_text = VARIABLE_PATTERN.sub(_replace_cb, template)

        return RenderResult(
            rendered_text=rendered_text,
            resolved_variables=resolved,
            unresolved_variables=unresolved,
            was_rendered=True,
        )

    def extract_variables(self, template: str) -> list[VariableInfo]:
        matches = VARIABLE_PATTERN.findall(template)
        result = []
        seen = set()
        for name, fallback in matches:
            stripped_name = name.strip()
            fb = fallback.strip() if fallback and fallback.strip() else None
            if fb == "":
                fb = None
            raw_match = f"{{{{{name}" + (f":{fallback}" if fallback else "") + "}}"
            key = stripped_name.lower()
            if key not in seen:
                seen.add(key)
                result.append(
                    VariableInfo(
                        name=stripped_name,
                        fallback=fb,
                        source_type=classify_source(stripped_name),
                        raw_match=raw_match,
                    )
                )
        return result

    def resolve_variable(
        self,
        var_name: str,
        fallback: Optional[str],
        lead,
        agent=None,
        custom_fallbacks: dict[str, str] | None = None,
    ) -> str:
        value, _ = self._resolve(var_name, fallback, lead, agent, custom_fallbacks)
        return value

    def _resolve(
        self,
        var_name: str,
        fallback: Optional[str],
        lead,
        agent=None,
        custom_fallbacks: dict[str, str] | None = None,
    ) -> tuple[str, bool]:
        normalized = var_name.lower().strip()
        used_fallback = False

        # 1. Lead standard fields
        if normalized in LEAD_STANDARD_FIELDS:
            field_attr = LEAD_STANDARD_FIELDS[normalized]
            value = self._get_lead_attr(lead, field_attr)
            if value:
                return self._sanitize_value(str(value)), False

        # 2. Lead custom fields (JSONB)
        custom = self._get_lead_attr(lead, "custom_fields")
        if custom and isinstance(custom, dict):
            key_map = {k.lower(): k for k in custom}
            if normalized in key_map:
                raw_val = custom[key_map[normalized]]
                if raw_val is not None:
                    return self._sanitize_value(str(raw_val)), False

        # 3. System variables
        if normalized in SYSTEM_VARIABLES:
            resolver = SYSTEM_VARIABLES[normalized]
            if callable(resolver):
                return self._sanitize_value(str(resolver())), False
            if agent and normalized == "agent_name":
                name_val = getattr(agent, "name", None)
                if name_val:
                    return self._sanitize_value(str(name_val)), False

        # 4. Inline fallback
        if fallback is not None and fallback != "":
            return self._sanitize_value(fallback), False

        # 5. Custom fallbacks dict
        if custom_fallbacks and normalized in custom_fallbacks:
            return self._sanitize_value(custom_fallbacks[normalized]), False

        # 6. Type-based fallback
        used_fallback = True
        var_type = self._infer_variable_type(normalized)
        if var_type in FALLBACK_BY_TYPE:
            return FALLBACK_BY_TYPE[var_type], used_fallback

        # 7. Global fallback
        return settings.VARIABLE_DEFAULT_FALLBACK, used_fallback

    @staticmethod
    def _get_lead_attr(lead, attr: str) -> Optional[str]:
        if isinstance(lead, dict):
            return lead.get(attr)
        if hasattr(lead, attr):
            return getattr(lead, attr, None)
        return None

    @staticmethod
    def _sanitize_value(value: str) -> str:
        sanitized = value.strip()
        for pattern in INJECTION_PATTERNS:
            if pattern.search(sanitized):
                logger.warning(
                    "Prompt injection pattern detected in variable value, truncating",
                    extra={
                        "pattern": pattern.pattern,
                        "original_length": len(sanitized),
                    },
                )
                sanitized = sanitized[:50] + "... [truncated for safety]"
                return sanitized
        if len(sanitized) > settings.MAX_VARIABLE_VALUE_LENGTH:
            logger.info(
                "Variable value exceeds max length, truncating",
                extra={
                    "max_length": settings.MAX_VARIABLE_VALUE_LENGTH,
                    "original_length": len(sanitized),
                },
            )
            sanitized = (
                sanitized[: settings.MAX_VARIABLE_VALUE_LENGTH] + "... [truncated]"
            )
        return sanitized

    @staticmethod
    def _infer_variable_type(var_name: str) -> str:
        for var_type, pattern in VARIABLE_TYPE_PATTERNS.items():
            if pattern.search(var_name):
                return var_type
        return "generic"
