"""Script generation service with RAG pipeline, grounding, and confidence scoring.

Orchestrates: retrieve → ground → generate → validate → cache.
"""

import asyncio
from dataclasses import dataclass
import hashlib
import json
import logging
import time
from typing import Optional

from sqlalchemy import text

from services.knowledge_search import search_knowledge_chunks
from services.grounding import GroundingService, GroundingResult
from services.llm.service import LLMService
from services.prompt_sanitizer import sanitize_template, sanitize_kb_content
from services.token_counting import count_tokens, will_exceed_budget

from config.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are an AI assistant for sales calls. You provide accurate, helpful responses "
    "based on the knowledge base content. Use only the provided context "
    "to answer questions. If the context does not contain enough information, "
    "respond with a 'I don't have that specific information available right now. "
    "Could I get your contact details so someone from our team can "
    "follow up with the answer?'"
)

GROUNDING_INSTRUCTIONS = {
    "strict": (
        "You MUST answer based ONLY on the provided context. "
        "If the context does not contain enough information to answer "
        "the question, respond with: "
        "\"I don't have that specific information available right now. "
        "Could I get your contact details so someone from our team can "
        'follow up with the answer?" '
        "Do NOT make up facts or use external knowledge."
    ),
    "balanced": (
        "Answer primarily based on the provided context. "
        "You may supplement with general knowledge, but clearly mark "
        "any information not from the context with: "
        '"[General knowledge]". '
        "If the context is insufficient, acknowledge the limitation "
        "and suggest the lead speak with a team member."
    ),
    "creative": (
        "Use the provided context as your primary source. "
        "You may expand with relevant knowledge, but remain factual. "
        "Flag any claims not directly supported by the context with: "
        '"[Additional context]". '
        "Exercise caution with specific claims about pricing, terms, "
        "or guarantees — always defer to the provided context for these."
    ),
}

NO_KNOWLEDGE_FALLBACK = (
    "I don't have that specific information available right now. "
    "Could I get your contact details so someone from our team can "
    "follow up with the answer?"
)


class AgentNotFoundError(Exception):
    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        super().__init__(f"Agent {agent_id} not found")


class AgentOwnershipError(Exception):
    def __init__(self, agent_id: int, org_id: str):
        self.agent_id = agent_id
        self.org_id = org_id
        super().__init__(f"Agent {agent_id} does not belong to org {org_id}")


@dataclass
class ScriptGenerationResult:
    response: str
    grounding_confidence: float
    is_low_confidence: bool
    source_chunks: list[dict]
    model: str
    latency_ms: float
    grounding_mode: str
    was_truncated: bool
    cached: bool
    config_version: Optional[int] = None
    cost_estimate: float = 0.0
    was_corrected: bool = False
    correction_count: int = 0
    verification_timed_out: bool = False


class ScriptGenerationService:
    def __init__(
        self,
        llm_service: LLMService | None = None,
        embedding_service=None,
        session=None,
        redis_client=None,
    ):
        self._llm = llm_service
        self._embedding = embedding_service
        self._session = session
        self._redis = redis_client

    async def generate_response(
        self,
        query: str,
        org_id: str,
        agent_id: int | None = None,
        grounding_mode: str = "strict",
        max_source_chunks: int = 5,
        system_prompt_template: str | None = None,
        min_confidence: float = 0.5,
        lead_id: int | None = None,
        script_id: int | None = None,
        factual_hook_enabled: bool = True,
    ) -> ScriptGenerationResult:
        if (lead_id is None) != (script_id is None):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=422,
                detail={
                    "code": "invalid_params",
                    "message": "Both lead_id and script_id must be provided together, or neither.",
                },
            )

        start = time.monotonic()

        render_result = None
        if (
            lead_id is not None
            and script_id is not None
            and settings.VARIABLE_INJECTION_ENABLED
        ):
            from services.variable_injection import VariableInjectionService
            from services.shared_queries import (
                load_script_for_context,
                load_lead_for_context,
            )

            injection_svc = VariableInjectionService(self._session)
            script = await load_script_for_context(self._session, script_id, org_id)
            lead = await load_lead_for_context(self._session, lead_id, org_id)
            render_result = await asyncio.wait_for(
                injection_svc.render_template(script.content, lead),
                timeout=settings.VARIABLE_RESOLUTION_TIMEOUT_MS / 1000,
            )
            query = sanitize_template(render_result.rendered_text)

        cache_key = f"script_gen:{org_id}:{agent_id or 'default'}:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
        if lead_id is not None and script_id is not None:
            cache_key += f":l{lead_id}:s{script_id}"

        cached = await self._check_cache_by_key(cache_key)
        if cached:
            try:
                cached_data = json.loads(cached)
                cached_data.setdefault("was_corrected", False)
                cached_data.setdefault("correction_count", 0)
                cached_data.setdefault("verification_timed_out", False)
                latency_ms = (time.monotonic() - start) * 1000
                cached_data["latency_ms"] = latency_ms
                cached_data["cached"] = True
                return ScriptGenerationResult(**cached_data)
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "Failed to deserialize cached result, treating as cache miss"
                )

        query_embedding = await self._embedding.generate_embedding(query)
        kb_ids = None
        if agent_id is not None:
            kb_ids = await self._get_agent_knowledge_base_ids(agent_id, org_id)

        if render_result and render_result.was_rendered:
            budget = settings.AI_LLM_MAX_TOKENS - settings.TOKEN_RESERVATION
            query_tokens = self._count_tokens(query)
            if query_tokens > budget:
                logger.error(
                    "Rendered template exceeds entire token budget, truncating",
                    extra={"query_tokens": query_tokens, "budget": budget},
                )
                max_chars = int(budget * 3.5)
                query = query[:max_chars] + "... [truncated for token budget]"
            elif query_tokens > (budget * 0.5):
                logger.warning(
                    "Rendered template consumes >50%% of context budget",
                    extra={"query_tokens": query_tokens, "budget": budget},
                )

        chunks, total_scanned = await self._retrieve_context(
            query_embedding, org_id, kb_ids, max_source_chunks
        )

        if not chunks:
            total_all = total_scanned
            event_type = (
                "empty_knowledge_base" if total_all == 0 else "no_relevant_chunks"
            )
            latency_ms = (time.monotonic() - start) * 1000

            self._log_audit(
                event_type=event_type,
                query=query,
                org_id=org_id,
                confidence=0.0,
                chunks=[],
                total_scanned=total_all,
                max_similarity=0.0,
                latency_ms=latency_ms,
                grounding_mode=grounding_mode,
            )

            return ScriptGenerationResult(
                response=NO_KNOWLEDGE_FALLBACK,
                grounding_confidence=0.0,
                is_low_confidence=True,
                source_chunks=[],
                model=settings.AI_LLM_MODEL,
                latency_ms=latency_ms,
                grounding_mode=grounding_mode,
                was_truncated=False,
                cached=False,
                cost_estimate=0.0,
            )

        system_prompt, user_message, was_truncated, has_context = (
            self._build_grounded_prompt(
                query, chunks, grounding_mode, system_prompt_template
            )
        )

        if not has_context and not was_truncated:
            latency_ms = (time.monotonic() - start) * 1000
            self._log_audit(
                event_type="no_relevant_chunks",
                query=query,
                org_id=org_id,
                confidence=0.0,
                chunks=[],
                total_scanned=total_scanned,
                max_similarity=0.0,
                latency_ms=latency_ms,
                grounding_mode=grounding_mode,
            )
            return ScriptGenerationResult(
                response=NO_KNOWLEDGE_FALLBACK,
                grounding_confidence=0.0,
                is_low_confidence=True,
                source_chunks=[],
                model=settings.AI_LLM_MODEL,
                latency_ms=latency_ms,
                grounding_mode=grounding_mode,
                was_truncated=False,
                cached=False,
                cost_estimate=0.0,
            )

        llm_response = await self._call_llm_with_retry(system_prompt, user_message)

        grounding_result = GroundingService.compute_confidence(
            chunks=chunks,
            response=llm_response,
            max_source_chunks=max_source_chunks,
            min_confidence=min_confidence,
        )

        hook_was_corrected = False
        hook_correction_count = 0
        hook_verification_timed_out = False

        if (
            settings.FACTUAL_HOOK_ENABLED
            and factual_hook_enabled
            and not cached
            and grounding_result.score > 0
        ):
            from services.factual_hook import FactualHookService

            hook = FactualHookService(self._session, self._llm, self._embedding)
            try:
                hook_result = await asyncio.wait_for(
                    hook.verify_and_correct(
                        response=llm_response,
                        source_chunks=chunks,
                        query=query,
                        org_id=org_id,
                        knowledge_base_ids=kb_ids,
                    ),
                    timeout=settings.FACTUAL_HOOK_VERIFICATION_TIMEOUT_MS / 1000,
                )
                if hook_result.was_corrected:
                    llm_response = hook_result.final_response
                    grounding_result = GroundingService.compute_confidence(
                        chunks=chunks,
                        response=llm_response,
                        max_source_chunks=max_source_chunks,
                        min_confidence=min_confidence,
                    )
                hook_was_corrected = hook_result.was_corrected
                hook_correction_count = hook_result.correction_count
                hook_verification_timed_out = hook_result.verification_timed_out
            except asyncio.TimeoutError:
                logger.warning(
                    "Factual hook timed out after %dms",
                    settings.FACTUAL_HOOK_VERIFICATION_TIMEOUT_MS,
                    extra={
                        "org_id": org_id,
                        "query_hash": hashlib.sha256(query.encode()).hexdigest()[:8],
                    },
                )
                result = ScriptGenerationResult(
                    response=llm_response,
                    grounding_confidence=grounding_result.score,
                    is_low_confidence=grounding_result.is_low_confidence,
                    source_chunks=chunks,
                    model=settings.AI_LLM_MODEL,
                    latency_ms=(time.monotonic() - start) * 1000,
                    grounding_mode=grounding_mode,
                    was_truncated=grounding_result.was_truncated or was_truncated,
                    cached=False,
                    cost_estimate=self._estimate_cost(
                        system_prompt, user_message, llm_response
                    ),
                    was_corrected=False,
                    correction_count=0,
                    verification_timed_out=True,
                )
                await self._cache_result(
                    query,
                    org_id,
                    agent_id,
                    result,
                    lead_id=lead_id,
                    script_id=script_id,
                    ttl=60,
                )
                return result

        latency_ms = (time.monotonic() - start) * 1000
        max_similarity = max(c["similarity"] for c in chunks) if chunks else 0.0
        cost = self._estimate_cost(system_prompt, user_message, llm_response)

        result = ScriptGenerationResult(
            response=llm_response,
            grounding_confidence=grounding_result.score,
            is_low_confidence=grounding_result.is_low_confidence,
            source_chunks=chunks,
            model=settings.AI_LLM_MODEL,
            latency_ms=latency_ms,
            grounding_mode=grounding_mode,
            was_truncated=grounding_result.was_truncated or was_truncated,
            cached=False,
            config_version=None,
            cost_estimate=cost,
            was_corrected=hook_was_corrected,
            correction_count=hook_correction_count,
            verification_timed_out=hook_verification_timed_out,
        )

        await self._cache_result(
            query, org_id, agent_id, result, lead_id=lead_id, script_id=script_id
        )

        self._log_audit(
            event_type="generation_completed",
            query=query,
            org_id=org_id,
            confidence=grounding_result.score,
            chunks=chunks,
            total_scanned=total_scanned,
            max_similarity=max_similarity,
            latency_ms=latency_ms,
            grounding_mode=grounding_mode,
            was_truncated=was_truncated,
            cost=cost,
            extra_fields={
                "script_id": script_id,
                "lead_id": lead_id,
                "variable_count": len(render_result.resolved_variables)
                if render_result
                else 0,
                "unresolved_variables": render_result.unresolved_variables
                if render_result
                else [],
            },
        )

        return result

    async def _retrieve_context(
        self,
        query_embedding,
        org_id,
        knowledge_base_ids=None,
        max_chunks=5,
    ):
        chunks = await search_knowledge_chunks(
            session=self._session,
            query_embedding=query_embedding,
            org_id=org_id,
            max_chunks=max_chunks,
            knowledge_base_ids=knowledge_base_ids,
        )
        try:
            total_scanned = await self._count_total_chunks(org_id, knowledge_base_ids)
        except Exception:
            total_scanned = len(chunks)
        return chunks, total_scanned

    async def _count_total_chunks(self, org_id, knowledge_base_ids=None):
        kb_filter = ""
        params = {"org_id": org_id}
        if knowledge_base_ids:
            kb_filter = "AND kc.knowledge_base_id = ANY(:kb_ids) "
            params["kb_ids"] = knowledge_base_ids

        result = await self._session.execute(
            text(
                "SELECT COUNT(*) FROM knowledge_chunks kc "
                "JOIN knowledge_bases kb ON kc.knowledge_base_id = kb.id "
                "WHERE kc.org_id = :org_id "
                "AND kc.soft_delete = false "
                "AND kb.status = 'ready' "
                "AND kb.soft_delete = false "
                f"{kb_filter}"
            ),
            params,
        )
        return result.scalar_one()

    async def _get_agent_knowledge_base_ids(self, agent_id, org_id):
        agent = await self._session.execute(
            text(
                "SELECT id, org_id, knowledge_base_ids FROM agents "
                "WHERE id = :agent_id AND soft_delete = false"
            ),
            {"agent_id": agent_id},
        )
        row = agent.first()
        if row is None:
            raise AgentNotFoundError(agent_id)
        if row[1] != org_id:
            raise AgentOwnershipError(agent_id, org_id)
        return row[2]

    def _build_grounded_prompt(
        self,
        query,
        chunks,
        grounding_mode,
        system_prompt_template=None,
    ):
        base_system = sanitize_template(system_prompt_template or DEFAULT_SYSTEM_PROMPT)
        grounding_instruction = GROUNDING_INSTRUCTIONS.get(
            grounding_mode, GROUNDING_INSTRUCTIONS[settings.GROUNDING_DEFAULT_MODE]
        )
        system_prompt = f"{base_system}\n\n{grounding_instruction}"

        sorted_chunks = sorted(chunks, key=lambda c: c["similarity"], reverse=True)
        budget = settings.AI_LLM_MAX_TOKENS - settings.TOKEN_RESERVATION
        context_parts = []
        was_truncated = False
        for i, c in enumerate(sorted_chunks):
            content = sanitize_kb_content(c["content"])
            part = f"[Source {i + 1}] (similarity: {c['similarity']:.2f}):\n{content}"
            context_text = "\n\n".join(context_parts + [part])
            user_message = f"Context:\n{context_text}\n\nQuestion: {query}"
            estimated_tokens = self._count_tokens(system_prompt + user_message)
            if estimated_tokens > budget:
                was_truncated = True
                break
            context_parts.append(part)

        if was_truncated:
            logger.warning(
                "Prompt truncated: %d/%d chunks fit within token budget",
                len(context_parts),
                len(sorted_chunks),
            )

        final_context = "\n\n".join(context_parts)
        user_message = f"Context:\n{final_context}\n\nQuestion: {query}"
        return system_prompt, user_message, was_truncated, bool(context_parts)

    def _count_tokens(self, text: str) -> int:
        return count_tokens(
            text, model=settings.AI_LLM_MODEL, provider=settings.AI_PROVIDER
        )

    @staticmethod
    def _estimate_token_count(text):
        return len(text) // 4

    async def _call_llm_with_retry(self, system_prompt, user_message):
        last_error = None
        for attempt in range(settings.LLM_MAX_RETRIES + 1):
            try:
                response = await self._llm.generate(
                    system=system_prompt,
                    user=user_message,
                    temperature=settings.AI_LLM_TEMPERATURE,
                    max_tokens=settings.TOKEN_RESERVATION,
                )
                return response
            except Exception as e:
                last_error = e
                if attempt < settings.LLM_MAX_RETRIES:
                    delay = settings.LLM_RETRY_BACKOFF_BASE * (2**attempt)
                    logger.warning(
                        "LLM call attempt %d failed, retrying in %.1fs",
                        attempt + 1,
                        delay,
                        extra={
                            "provider": settings.AI_PROVIDER,
                            "model": settings.AI_LLM_MODEL,
                            "error": str(e),
                            "attempt": attempt + 1,
                        },
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "LLM call failed after %d retries",
                        attempt + 1,
                        extra={
                            "provider": settings.AI_PROVIDER,
                            "model": settings.AI_LLM_MODEL,
                            "error": str(e),
                            "retry_count": attempt + 1,
                        },
                    )
        raise last_error or RuntimeError("LLM call failed with no error captured")

    async def _check_cache(self, query, org_id, agent_id=None):
        cache_key = f"script_gen:{org_id}:{agent_id or 'default'}:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
        return await self._check_cache_by_key(cache_key)

    async def _check_cache_by_key(self, cache_key):
        if not self._redis:
            return None
        try:
            cached = await self._redis.get(cache_key)
            return cached
        except Exception as e:
            logger.warning("Redis cache lookup failed: %s", e)
            return None

    async def _cache_result(
        self, query, org_id, agent_id, result, lead_id=None, script_id=None, ttl=None
    ):
        if not self._redis:
            return
        cache_key = f"script_gen:{org_id}:{agent_id or 'default'}:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
        if lead_id is not None and script_id is not None:
            cache_key += f":l{lead_id}:s{script_id}"
        try:
            data = json.dumps(
                {
                    "response": result.response,
                    "grounding_confidence": result.grounding_confidence,
                    "is_low_confidence": result.is_low_confidence,
                    "source_chunks": result.source_chunks,
                    "model": result.model,
                    "grounding_mode": result.grounding_mode,
                    "was_truncated": result.was_truncated,
                    "cost_estimate": result.cost_estimate,
                    "was_corrected": result.was_corrected,
                    "correction_count": result.correction_count,
                    "verification_timed_out": result.verification_timed_out,
                }
            )
            cache_ttl = ttl if ttl is not None else settings.SCRIPT_GENERATION_CACHE_TTL
            await self._redis.setex(
                cache_key,
                cache_ttl,
                data,
            )
        except Exception as e:
            logger.warning("Redis cache write failed: %s", e)

    async def invalidate_cache(self, org_id, agent_id):
        if not self._redis:
            return
        cache_key = f"script_gen:{org_id}:{agent_id}:*"
        try:
            keys = []
            async for key in self._redis.scan_iter(match=cache_key):
                keys.append(key)
            if keys:
                await self._redis.delete(*keys)
        except Exception as e:
            logger.warning("Redis cache invalidation failed: %s", e)

    def _estimate_cost(self, system_prompt, user_message, llm_response):
        if not settings.COST_TRACKING_ENABLED:
            return 0.0
        from services.model_catalog import compute_cost

        input_tokens = self._count_tokens(system_prompt + user_message)
        output_tokens = self._count_tokens(llm_response)
        return compute_cost(settings.AI_LLM_MODEL, input_tokens, output_tokens)

    def _log_audit(
        self,
        event_type,
        query,
        org_id,
        confidence,
        chunks,
        total_scanned=None,
        max_similarity=None,
        latency_ms=0.0,
        grounding_mode="strict",
        was_truncated=False,
        cost=0.0,
        extra_fields: dict | None = None,
    ):
        log_data = {
            "org_id": org_id,
            "query": query[:200]
            if not extra_fields
            else "[variable-injected query redacted for PII]",
            "grounding_confidence": round(confidence, 4),
            "model": settings.AI_LLM_MODEL,
            "latency_ms": round(latency_ms, 2),
            "grounding_mode": grounding_mode,
            "cost_estimate": cost,
            "was_truncated": was_truncated,
        }
        if event_type == "no_relevant_chunks":
            log_data["total_chunks_scanned"] = total_scanned
            log_data["max_similarity"] = (
                round(max_similarity, 4) if max_similarity else 0.0
            )
            log_data["threshold"] = settings.RAG_SIMILARITY_THRESHOLD
        elif event_type == "empty_knowledge_base":
            log_data["event_type"] = "empty_knowledge_base"
        else:
            log_data["source_chunks"] = [
                {"chunk_id": c["chunk_id"], "similarity": round(c["similarity"], 3)}
                for c in chunks
            ]

        if extra_fields:
            log_data.update(extra_fields)

        logger.info(
            "Script generation %s",
            event_type,
            extra=log_data,
        )
