"""Grounding service for computing confidence scores.

Implements No-Knowledge-No-Answer policy enforcement and source attribution estimation.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GroundingResult:
    score: float
    chunk_coverage: float
    avg_similarity: float
    attribution_ratio: float
    is_low_confidence: bool
    source_chunk_ids: list[int]
    was_truncated: bool


class GroundingService:
    @staticmethod
    def compute_confidence(
        chunks: list[dict],
        response: str,
        max_source_chunks: int = 5,
        min_confidence: float = 0.5,
    ) -> GroundingResult:
        if not chunks:
            return GroundingResult(
                score=0.0,
                chunk_coverage=0.0,
                avg_similarity=0.0,
                attribution_ratio=0.0,
                is_low_confidence=True,
                source_chunk_ids=[],
                was_truncated=False,
            )

        chunk_ids = [c["chunk_id"] for c in chunks]

        chunk_coverage = min(1.0, len(chunks) / max_source_chunks)
        avg_similarity = sum(c["similarity"] for c in chunks) / len(chunks)
        attribution_ratio = GroundingService.estimate_source_attribution(
            chunks, response
        )

        score = chunk_coverage * 0.3 + avg_similarity * 0.4 + attribution_ratio * 0.3

        is_low = score < min_confidence

        return GroundingResult(
            score=round(score, 4),
            chunk_coverage=round(chunk_coverage, 4),
            avg_similarity=round(avg_similarity, 4),
            attribution_ratio=round(attribution_ratio, 4),
            is_low_confidence=is_low,
            source_chunk_ids=chunk_ids,
            was_truncated=False,
        )

    @staticmethod
    def estimate_source_attribution(chunks: list[dict], response: str) -> float:
        if not response or not response.strip():
            return 0.0

        response_words = response.lower().split()
        response_unigrams = set(response_words)
        response_bigrams = set(zip(response_words, response_words[1:]))

        source_text = " ".join(c["content"] for c in chunks).lower()
        source_words = source_text.split()
        source_unigrams = set(source_words)
        source_bigrams = set(zip(source_words, source_words[1:]))

        if not response_unigrams:
            return 0.0

        unigram_overlap = len(response_unigrams & source_unigrams) / len(
            response_unigrams
        )

        bigram_overlap = 0.0
        if response_bigrams:
            bigram_overlap = len(response_bigrams & source_bigrams) / len(
                response_bigrams
            )

        return min(1.0, unigram_overlap * 0.4 + bigram_overlap * 0.6)
