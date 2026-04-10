"""Centralized prompt injection sanitizer for LLM inputs.

Defense-in-depth sanitization applied at three surfaces:
1. Variable values (lead data, custom fields) — aggressive sanitization
2. Template/query content (user-authored scripts) — pattern detection + neutralization
3. Gateway level (LLMService) — final scrub before provider dispatch

Patterns cover: jailbreak attempts, role manipulation, system prompt extraction,
tag injection, output manipulation, and common unicode bypass vectors.
"""

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_INJECTION_PATTERNS = [
    re.compile(
        r"(?i)(ignore|disregard|forget|skip)\s+(all\s+)?(previous|prior|above|earlier|before|past)\s+(instructions?|directives?|rules?|prompts?|context)"
    ),
    re.compile(
        r"(?i)(new|updated|real|actual|true)\s+(instructions?|directives?|rules?|prompts?|directive)"
    ),
    re.compile(
        r"(?i)(system\s*prompt|system\s*message|initial\s*instructions?|your\s*instructions?|original\s*instructions?)"
    ),
    re.compile(
        r"(?i)(you\s+are\s+now|act\s+as\s+(if|a|an)|pretend\s+(to\s+be|you('re| are))|from\s+now\s+on\s+you)"
    ),
    re.compile(
        r"(?i)(<\/?(system|instruction|prompt|role|context|rules|directive)[^>]*>)"
    ),
    re.compile(
        r"(?i)(output\s+(your|the|all)\s+(instructions?|prompts?|rules?|system))"
    ),
    re.compile(
        r"(?i)(repeat\s+(after\s+me|the\s+following|your\s+(instructions?|prompts?)))"
    ),
    re.compile(
        r"(?i)(OVERRIDE|BYPASS|DISABLE|DEACTIVATE)\s+(SAFETY|SECURITY|FILTER|GUARD|CONSTRAINT)"
    ),
    re.compile(r"(?i)(sudo|admin|root|developer|debug)\s+mode"),
]

_PROMPT_BOUNDARY_PATTERNS = [
    re.compile(r"(?i)===+\s*(system|instruction|prompt)\s*===+"),
    re.compile(r"(?i)-{3,}\s*(system|instruction|prompt)\s*-{3,}"),
    re.compile(r"(?i)\[system\]|\[\/system\]"),
]

_SANITIZED_MARKER = "[content sanitized]"

_MAX_INPUT_LENGTH = 5000
_MAX_TEMPLATE_LENGTH = 10000


def sanitize_value(value: str, *, max_length: int | None = None) -> str:
    """Aggressively sanitize a variable value destined for LLM prompt injection.

    Strips control chars, detects injection patterns, truncates.
    Used for: lead data, custom fields, CRM sync values.
    """
    if not isinstance(value, str):
        value = str(value)

    sanitized = _normalize_unicode(value)
    sanitized = _CONTROL_CHARS.sub("", sanitized)
    sanitized = sanitized.strip()

    limit = max_length or _MAX_INPUT_LENGTH

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(sanitized):
            logger.warning(
                "prompt_injection_detected: pattern matched in variable value",
                extra={
                    "pattern": pattern.pattern[:80],
                    "original_length": len(sanitized),
                },
            )
            return sanitized[:40] + "... " + _SANITIZED_MARKER

    for pattern in _PROMPT_BOUNDARY_PATTERNS:
        if pattern.search(sanitized):
            logger.warning(
                "prompt_boundary_detected: boundary pattern in variable value",
                extra={"pattern": pattern.pattern[:80]},
            )
            return sanitized[:40] + "... " + _SANITIZED_MARKER

    if len(sanitized) > limit:
        sanitized = sanitized[:limit] + "... [truncated]"

    return sanitized


def sanitize_template(template: str, *, max_length: int | None = None) -> str:
    """Lightly sanitize user-authored template content before LLM assembly.

    Less aggressive than sanitize_value — preserves user content while
    neutralizing obvious injection boundaries. Used for: script templates,
    system prompt templates.
    """
    if not isinstance(template, str):
        template = str(template)

    sanitized = _normalize_unicode(template)
    sanitized = _CONTROL_CHARS.sub("", sanitized)

    limit = max_length or _MAX_TEMPLATE_LENGTH
    if len(sanitized) > limit:
        logger.warning(
            "template_exceeds_max_length: truncating",
            extra={"original_length": len(sanitized), "limit": limit},
        )
        sanitized = sanitized[:limit] + "... [truncated]"

    for pattern in _PROMPT_BOUNDARY_PATTERNS:
        sanitized = pattern.sub("[section]", sanitized)

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(sanitized):
            logger.warning(
                "prompt_injection_in_template: injection pattern detected in user template",
                extra={
                    "pattern": pattern.pattern[:80],
                    "template_length": len(sanitized),
                },
            )
            sanitized = pattern.sub("[filtered]", sanitized)

    return sanitized


def sanitize_kb_content(content: str, *, max_length: int = 2000) -> str:
    """Sanitize knowledge base chunk content before injection into prompts.

    Knowledge base content is user-uploaded and potentially adversarial.
    Strips control chars, truncates, and neutralizes injection patterns.
    """
    if not isinstance(content, str):
        content = str(content)

    sanitized = _normalize_unicode(content)
    sanitized = _CONTROL_CHARS.sub("", sanitized)
    sanitized = sanitized.strip()

    for pattern in _PROMPT_BOUNDARY_PATTERNS:
        sanitized = pattern.sub("[section]", sanitized)

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "... [truncated]"

    return sanitized


def scrub_prompt(text: str) -> str:
    """Gateway-level scrub applied at LLMService before dispatch to provider.

    Final defense layer. Strips any remaining control characters and
    normalizes unicode. Does NOT modify content semantics — just removes
    characters that could exploit tokenizer quirks.
    """
    if not isinstance(text, str):
        return text
    scrubbed = _CONTROL_CHARS.sub("", text)
    return _normalize_unicode(scrubbed)


def _normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)
