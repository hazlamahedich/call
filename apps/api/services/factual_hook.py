"""Factual hook service for real-time self-correction of AI-generated responses.

Extracts factual claims from LLM output, verifies them against the knowledge
base via secondary embedding + similarity search, and triggers a self-correction
loop for unsupported claims. Includes circuit breaker protection and timeout safety.
"""

import asyncio
import hashlib
import logging
import re
import time
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from models.factual_verification_log import FactualVerificationLog
from services.knowledge_search import search_knowledge_chunks
from services.llm.service import LLMService
from services.prompt_sanitizer import sanitize_kb_content

logger = logging.getLogger(__name__)

NO_KNOWLEDGE_FALLBACK = "I don't have that specific information available right now."


@dataclass
class ClaimVerification:
    claim_text: str
    is_supported: bool
    supporting_chunks: list[dict] = field(default_factory=list)
    max_similarity: float = 0.0
    verification_error: bool = False


@dataclass
class FactualHookResult:
    was_corrected: bool
    correction_count: int
    final_response: str
    original_response: str
    verified_claims: list[ClaimVerification] = field(default_factory=list)
    verification_timed_out: bool = False
    total_verification_ms: float = 0.0
    circuit_breaker_open: bool = False


_QUANTIFIED_RE = re.compile(
    r"\d+\.?\d*\s*%|\$\d+|\d+\s*"
    r"(percent|million|billion|thousand|users|clients|customers|calls|minutes|hours|dollars)",
    re.IGNORECASE,
)
_NAMED_ENTITY_RE = re.compile(r"(?<=[a-z\s])\s([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)")
_COMPARATIVE_RE = re.compile(
    r"\b(better|worse|more|less|faster|slower|cheaper|higher|lower)\s+than\s+(?!ever\b)",
    re.IGNORECASE,
)
_DEFINITIVE_RE = re.compile(
    r"\b(exactly|precisely|specifically|guaranteed)\b", re.IGNORECASE
)

_FILLER_RE = re.compile(
    r"(?:(?:I|we|you)\s+(?:will|would|can|could|should|must)\s+"
    r"(?:like|love|be happy|get back|follow up|help|reach out|let you know))"
    r"|(?:thank|thanks|please|feel free|don'?t hesitate)",
    re.IGNORECASE,
)
_PUFFERY_RE = re.compile(
    r"\b(enhance|elevate|transform|revolutionize|leverage|synergize|optimize)\b",
    re.IGNORECASE,
)
_QUESTION_RE = re.compile(r"\?\s*$")
_HEDGED_RE = re.compile(
    r"\b(?:I believe|I think|it seems|possibly|maybe|perhaps|in my opinion)\b",
    re.IGNORECASE,
)
_GREETING_RE = re.compile(
    r"^(?:hello|hi|hey|good morning|good afternoon|glad|pleased|welcome)\b",
    re.IGNORECASE,
)
_ABBREVIATIONS = frozenset(
    {
        "dr",
        "mr",
        "mrs",
        "ms",
        "prof",
        "sr",
        "jr",
        "st",
        "ave",
        "blvd",
        "inc",
        "ltd",
        "corp",
        "co",
        "dept",
        "est",
        "govt",
        "assn",
        "u.s",
        "u.k",
        "e.g",
        "i.e",
        "vs",
        "approx",
        "dept",
        "div",
        "eq",
    }
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


class FactualHookService:
    _consecutive_errors: int = 0
    _circuit_open: bool = False
    _circuit_opened_at: float = 0.0

    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService,
        embedding_service: object = None,
    ):
        self._session = session
        self._llm = llm_service
        self._embedding = embedding_service

    async def verify_and_correct(
        self,
        response: str,
        source_chunks: list[dict],
        query: str,
        org_id: str,
        knowledge_base_ids: list[int] | None = None,
        max_corrections: int | None = None,
        timeout_ms: int | None = None,
    ) -> FactualHookResult:
        mc = (
            max_corrections
            if max_corrections is not None
            else settings.FACTUAL_HOOK_MAX_CORRECTIONS
        )
        effective_timeout = (
            timeout_ms
            if timeout_ms is not None
            else settings.FACTUAL_HOOK_VERIFICATION_TIMEOUT_MS
        )
        timeout_s = effective_timeout / 1000.0
        start = time.monotonic()

        if self._check_circuit_breaker():
            return FactualHookResult(
                was_corrected=False,
                correction_count=0,
                final_response=response,
                original_response=response,
                verified_claims=[],
                verification_timed_out=False,
                total_verification_ms=time.monotonic() - start,
                circuit_breaker_open=True,
            )

        claims = self._extract_claims(response)
        if not claims:
            return FactualHookResult(
                was_corrected=False,
                correction_count=0,
                final_response=response,
                original_response=response,
                verified_claims=[],
                verification_timed_out=False,
                total_verification_ms=time.monotonic() - start,
            )

        current_response = response
        correction_count = 0
        verifications: list[ClaimVerification] = []

        async def _core_work():
            nonlocal current_response, correction_count, verifications
            per_claim_budget = settings.FACTUAL_HOOK_PER_CLAIM_TIMEOUT_MS / 1000.0
            per_correction_budget = (
                settings.FACTUAL_HOOK_PER_CORRECTION_TIMEOUT_MS / 1000.0
            )
            min_remaining = settings.FACTUAL_HOOK_MIN_REMAINING_BUDGET_MS / 1000.0
            for attempt in range(mc + 1):
                elapsed = time.monotonic() - start
                remaining = timeout_s - elapsed
                if remaining < min_remaining and attempt > 0:
                    logger.info(
                        "factual_hook_budget_exhausted: skipping correction round, %.0fms remaining",
                        remaining * 1000,
                    )
                    break

                current_claims = (
                    claims if attempt == 0 else self._extract_claims(current_response)
                )
                if not current_claims:
                    verifications = []
                    break

                try:
                    verifications = await asyncio.wait_for(
                        self._verify_all_claims(
                            current_claims,
                            org_id,
                            knowledge_base_ids,
                        ),
                        timeout=min(
                            per_claim_budget * max(1, len(current_claims)), remaining
                        ),
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "factual_hook_claim_verification_timeout: %.0fms budget for %d claims",
                        per_claim_budget * 1000,
                        len(current_claims),
                    )
                    break

                if all(v.is_supported for v in verifications):
                    break
                if attempt < mc:
                    unsupported = [v for v in verifications if not v.is_supported]
                    try:
                        current_response = await asyncio.wait_for(
                            self._correct_response(
                                current_response,
                                unsupported,
                                source_chunks,
                                query,
                            ),
                            timeout=min(per_correction_budget, remaining),
                        )
                        correction_count += 1
                    except asyncio.TimeoutError:
                        logger.warning(
                            "factual_hook_correction_timeout: correction LLM call exceeded %.0fms",
                            per_correction_budget * 1000,
                        )
                        break
                else:
                    unsupported = [v for v in verifications if not v.is_supported]
                    current_response = self._replace_unsupported_with_fallback(
                        current_response,
                        unsupported,
                    )

            if correction_count > 0:
                final_claims = self._extract_claims(current_response)
                if final_claims:
                    verifications = await self._verify_all_claims(
                        final_claims,
                        org_id,
                        knowledge_base_ids,
                    )
                else:
                    verifications = []

        timed_out = False
        try:
            await asyncio.wait_for(_core_work(), timeout=timeout_s)
        except asyncio.TimeoutError:
            timed_out = True
            logger.warning(
                "factual_hook_timeout: verification timed out after %.0fms",
                time.monotonic() - start,
            )

        result = FactualHookResult(
            was_corrected=(current_response != response),
            correction_count=correction_count,
            final_response=current_response,
            original_response=response,
            verified_claims=verifications,
            verification_timed_out=timed_out,
            total_verification_ms=time.monotonic() - start,
        )

        try:
            query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
            await self._log_verification(org_id, query_hash, result)
        except Exception as e:
            logger.warning("Failed to log verification result: %s", str(e)[:200])

        return result

    def _extract_claims(self, response: str) -> list[str]:
        raw_sentences = _SENTENCE_SPLIT_RE.split(response.strip())
        sentences: list[str] = []
        for s in raw_sentences:
            stripped = s.strip()
            if (
                stripped
                and stripped[-1] != "."
                and stripped[-1] != "!"
                and stripped[-1] != "?"
            ):
                if sentences:
                    word = sentences[-1].strip()
                    tail = word.rsplit(None, 1)[-1].rstrip(".").lower()
                    if tail in _ABBREVIATIONS:
                        sentences[-1] = sentences[-1] + " " + stripped
                        continue
            sentences.append(s)
        claims: list[str] = []
        min_len = settings.FACTUAL_HOOK_CLAIM_MIN_LENGTH

        for sentence in sentences:
            s = sentence.strip()
            if len(s) < min_len:
                continue
            if _QUESTION_RE.search(s):
                continue
            if _GREETING_RE.search(s):
                continue
            if _HEDGED_RE.search(s):
                continue
            if _FILLER_RE.search(s):
                continue
            if _PUFFERY_RE.search(s) and not _QUANTIFIED_RE.search(s):
                continue

            positive = (
                _QUANTIFIED_RE.search(s)
                or _NAMED_ENTITY_RE.search(s)
                or _COMPARATIVE_RE.search(s)
                or _DEFINITIVE_RE.search(s)
            )
            if positive:
                claims.append(s)

        return claims

    async def _verify_all_claims(
        self,
        claims: list[str],
        org_id: str,
        knowledge_base_ids: list[int] | None,
        threshold: float | None = None,
    ) -> list[ClaimVerification]:
        th = (
            threshold
            if threshold is not None
            else settings.FACTUAL_HOOK_SIMILARITY_THRESHOLD
        )
        tasks = [
            self._verify_claim(claim, org_id, knowledge_base_ids, th)
            for claim in claims
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        verifications: list[ClaimVerification] = []

        for claim, result in zip(claims, results):
            if isinstance(result, Exception):
                self._record_error()
                logger.warning(
                    "Claim verification failed: %s",
                    str(result)[:200],
                    extra={"claim_prefix": claim[:50]},
                )
                verifications.append(
                    ClaimVerification(
                        claim_text=claim,
                        is_supported=False,
                        supporting_chunks=[],
                        max_similarity=0.0,
                        verification_error=True,
                    )
                )
            else:
                self._record_success()
                verifications.append(result)

        return verifications

    async def _verify_claim(
        self,
        claim: str,
        org_id: str,
        knowledge_base_ids: list[int] | None,
        threshold: float,
    ) -> ClaimVerification:
        if self._embedding is None:
            return ClaimVerification(
                claim_text=claim,
                is_supported=False,
                supporting_chunks=[],
                max_similarity=0.0,
                verification_error=True,
            )
        claim_embedding = await self._embedding.generate_embedding(
            claim, task_type="RETRIEVAL_QUERY"
        )
        results = await search_knowledge_chunks(
            self._session,
            claim_embedding,
            org_id,
            max_chunks=3,
            threshold=threshold,
            knowledge_base_ids=knowledge_base_ids,
        )
        max_sim = max((r["similarity"] for r in results), default=0.0)
        return ClaimVerification(
            claim_text=claim,
            is_supported=(max_sim >= threshold and len(results) > 0),
            supporting_chunks=results,
            max_similarity=max_sim,
        )

    def _check_circuit_breaker(self) -> bool:
        if not self._circuit_open:
            return False
        elapsed = time.monotonic() - self._circuit_opened_at
        if elapsed >= settings.FACTUAL_HOOK_CIRCUIT_BREAKER_RESET_SECONDS:
            FactualHookService._circuit_open = False
            FactualHookService._consecutive_errors = 0
            logger.info("Factual hook circuit breaker reset after %.0fs", elapsed)
            return False
        return True

    @classmethod
    def _record_error(cls):
        cls._consecutive_errors += 1
        if cls._consecutive_errors >= settings.FACTUAL_HOOK_CIRCUIT_BREAKER_THRESHOLD:
            cls._circuit_open = True
            cls._circuit_opened_at = time.monotonic()
            logger.warning(
                "factual_hook_circuit_open: circuit breaker OPENED after %d consecutive errors",
                cls._consecutive_errors,
            )

    @classmethod
    def _record_success(cls):
        cls._consecutive_errors = 0

    async def _correct_response(
        self,
        original_response: str,
        unsupported_claims: list[ClaimVerification],
        source_chunks: list[dict],
        query: str,
    ) -> str:
        unsupported_text = "\n".join(
            f"- {c.claim_text[:200]}" for c in unsupported_claims
        )
        context_text = "\n\n".join(
            sanitize_kb_content(c.get("content", ""))[:500] for c in source_chunks[:5]
        )

        correction_prompt = (
            "You previously generated a response that contained claims not supported "
            "by the knowledge base. Here are the unsupported claims:\n"
            f"{unsupported_text}\n\n"
            "Available knowledge base context:\n"
            f"{context_text}\n\n"
            "Please re-generate your response following these rules:\n"
            "1. Keep ALL claims that are supported by the context unchanged\n"
            "2. Re-phrase unsupported claims using ONLY information from the context\n"
            f'3. For claims that cannot be supported, use: "{NO_KNOWLEDGE_FALLBACK}"\n'
            "4. Do NOT add new claims not present in the context"
        )

        last_error = None
        for attempt in range(settings.LLM_MAX_RETRIES):
            try:
                return await self._llm.generate(
                    system=correction_prompt,
                    user=original_response,
                    temperature=settings.AI_LLM_TEMPERATURE,
                    max_tokens=settings.TOKEN_RESERVATION,
                )
            except Exception as e:
                last_error = e
                if attempt < settings.LLM_MAX_RETRIES - 1:
                    delay = settings.LLM_RETRY_BACKOFF_BASE * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Correction LLM call failed after %d retries: %s",
                        settings.LLM_MAX_RETRIES,
                        str(e)[:200],
                    )

        return original_response

    def _replace_unsupported_with_fallback(
        self,
        response: str,
        unsupported_claims: list[ClaimVerification],
    ) -> str:
        sentences = _SENTENCE_SPLIT_RE.split(response)
        result_sentences: list[str] = []

        for sentence in sentences:
            replaced = False
            sent_tokens = set(sentence.lower().split())
            for claim in unsupported_claims:
                claim_tokens = set(claim.claim_text.lower().split())
                if not claim_tokens:
                    continue
                overlap = len(sent_tokens & claim_tokens) / len(claim_tokens)
                if overlap >= 0.5:
                    result_sentences.append(NO_KNOWLEDGE_FALLBACK)
                    replaced = True
                    break
            if not replaced:
                result_sentences.append(sentence)

        return " ".join(result_sentences)

    async def _log_verification(
        self,
        org_id: str,
        query_hash: str,
        result: FactualHookResult,
    ) -> None:
        log = FactualVerificationLog.model_validate(
            {
                "orgId": org_id,
                "queryHash": query_hash,
                "wasCorrected": result.was_corrected,
                "correctionCount": result.correction_count,
                "claimsTotal": len(result.verified_claims),
                "claimsSupported": sum(
                    1 for c in result.verified_claims if c.is_supported
                ),
                "claimsUnsupported": sum(
                    1
                    for c in result.verified_claims
                    if not c.is_supported and not c.verification_error
                ),
                "claimsErrored": sum(
                    1 for c in result.verified_claims if c.verification_error
                ),
                "verificationTimedOut": result.verification_timed_out,
                "totalVerificationMs": result.total_verification_ms,
            }
        )
        self._session.add(log)
        await self._session.flush()
