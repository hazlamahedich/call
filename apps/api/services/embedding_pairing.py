"""Auto-embedding pairing: automatically selects the matching embedding
provider, model, and dimensions based on the chosen LLM provider.

Mappings:
    openai → text-embedding-3-small (1536d)
    gemini → gemini-embedding-001   (3072d)

When OpenRouter is active, the pairing is inferred from the model name
prefix (e.g., model "gpt-4o-mini" → openai embedding).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingPairing:
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int


_PROVIDER_PAIRINGS: dict[str, EmbeddingPairing] = {
    "openai": EmbeddingPairing(
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
    ),
    "gemini": EmbeddingPairing(
        embedding_provider="google",
        embedding_model="gemini-embedding-001",
        embedding_dimensions=3072,
    ),
}

_MODEL_PREFIX_MAP: dict[str, str] = {
    "gpt-": "openai",
    "o1-": "openai",
    "o3-": "openai",
    "text-embedding-": "openai",
    "gemini-": "gemini",
    "google/": "gemini",
}


def resolve_pairing(
    *,
    llm_provider: str = "",
    llm_model: str = "",
) -> EmbeddingPairing:
    """Resolve the correct embedding pairing for a given LLM config.

    Priority:
    1. Direct provider match (llm_provider="openai" → openai embedding)
    2. Model name prefix inference (llm_model="gpt-4o-mini" → openai)
    3. Default fallback (openai)
    """
    provider = _infer_provider(llm_provider, llm_model)
    return _PROVIDER_PAIRINGS.get(provider, _PROVIDER_PAIRINGS["openai"])


def _infer_provider(llm_provider: str, llm_model: str) -> str:
    if llm_provider in _PROVIDER_PAIRINGS:
        return llm_provider

    for prefix, provider in _MODEL_PREFIX_MAP.items():
        if llm_model.startswith(prefix):
            return provider

    return "openai"
