"""Provider-aware token counting for LLM prompt budget enforcement.

Uses tiktoken for OpenAI models when available, falls back to a
heuristic estimator for other providers. The heuristic applies a
provider-specific correction factor for more accurate estimation.
"""

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

_CHARS_PER_TOKEN_OPENAI = 3.8
_CHARS_PER_TOKEN_GEMINI = 3.5
_CHARS_PER_TOKEN_DEFAULT = 4.0

_TIKTOKEN_AVAILABLE = False
_tiktoken_encoding = None

try:
    import tiktoken

    _TIKTOKEN_AVAILABLE = True
except ImportError:
    pass


def _get_tiktoken_encoding(model: str):
    global _tiktoken_encoding
    if not _TIKTOKEN_AVAILABLE:
        return None
    try:
        if _tiktoken_encoding is None:
            _tiktoken_encoding = tiktoken.encoding_for_model(model)
        return _tiktoken_encoding
    except KeyError:
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None


def count_tokens(text: str, *, model: str = "", provider: str = "") -> int:
    """Count tokens for a text string, using tiktoken when available.

    Args:
        text: The text to count tokens for.
        model: The model name (used to select tiktoken encoding).
        provider: The provider name (openai, gemini) for heuristic fallback.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0

    if _TIKTOKEN_AVAILABLE and (provider == "openai" or model.startswith("gpt")):
        encoding = _get_tiktoken_encoding(model)
        if encoding is not None:
            try:
                return len(encoding.encode(text))
            except Exception:
                pass

    chars_per_token = _CHARS_PER_TOKEN_DEFAULT
    if provider == "gemini" or model.startswith("gemini"):
        chars_per_token = _CHARS_PER_TOKEN_GEMINI
    elif provider == "openai" or model.startswith("gpt"):
        chars_per_token = _CHARS_PER_TOKEN_OPENAI

    return int(len(text) / chars_per_token)


def count_messages_tokens(
    messages: list[dict], *, model: str = "", provider: str = ""
) -> int:
    total = 0
    for msg in messages:
        total += 4  # message overhead (<|start|>role<|end|>content<|end|>)
        content = msg.get("content", "")
        if isinstance(content, str):
            total += count_tokens(content, model=model, provider=provider)
        role = msg.get("role", "")
        total += count_tokens(role, model=model, provider=provider)
    total += 2  # priming tokens
    return total


def will_exceed_budget(
    text: str,
    budget: int,
    *,
    model: str = "",
    provider: str = "",
) -> bool:
    return count_tokens(text, model=model, provider=provider) > budget
