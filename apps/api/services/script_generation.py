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


class ScriptGenerationService:
    def __init__(
        self,
        llm_service: LLMService,
        embedding_service,
        session,
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
    ) -> ScriptGenerationResult:
        start = time.monotonic()

        cached = await self._check_cache(query, org_id, agent_id)
        if cached:
            try:
                cached_data = json.loads(cached)
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

        system_prompt, user_message, was_truncated = self._build_grounded_prompt(
            query, chunks, grounding_mode, system_prompt_template
        )

        if not system_prompt:
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
        )

        await self._cache_result(query, org_id, agent_id, result)

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
        base_system = system_prompt_template or DEFAULT_SYSTEM_PROMPT
        grounding_instruction = GROUNDING_INSTRUCTIONS.get(
            grounding_mode, GROUNDING_INSTRUCTIONS[settings.GROUNDING_DEFAULT_MODE]
        )
        system_prompt = f"{base_system}\n\n{grounding_instruction}"

        sorted_chunks = sorted(chunks, key=lambda c: c["similarity"], reverse=True)
        budget = settings.AI_LLM_MAX_TOKENS - settings.TOKEN_RESERVATION
        context_parts = []
        was_truncated = False
        for i, c in enumerate(sorted_chunks):
            part = (
                f"[Source {i + 1}] (similarity: {c['similarity']:.2f}):\n{c['content']}"
            )
            context_text = "\n\n".join(context_parts + [part])
            user_message = f"Context:\n{context_text}\n\nQuestion: {query}"
            estimated_tokens = self._estimate_token_count(system_prompt + user_message)
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
        return system_prompt, user_message, was_truncated

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

    def _generate_no_knowledge_response(
        self,
        query,
        org_id,
        total_chunks_scanned,
        max_similarity,
        grounding_mode,
    ):
        return ScriptGenerationResult(
            response=NO_KNOWLEDGE_FALLBACK,
            grounding_confidence=0.0,
            is_low_confidence=True,
            source_chunks=[],
            model=settings.AI_LLM_MODEL,
            latency_ms=0.0,
            grounding_mode=grounding_mode,
            was_truncated=False,
            cached=False,
            cost_estimate=0.0,
        )

    async def _check_cache(self, query, org_id, agent_id=None):
        if not self._redis:
            return None
        cache_key = f"script_gen:{org_id}:{agent_id or 'default'}:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
        try:
            cached = await self._redis.get(cache_key)
            return cached
        except Exception as e:
            logger.warning("Redis cache lookup failed: %s", e)
            return None

    async def _cache_result(self, query, org_id, agent_id, result):
        if not self._redis:
            return
        cache_key = f"script_gen:{org_id}:{agent_id or 'default'}:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
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
                }
            )
            await self._redis.setex(
                cache_key,
                settings.SCRIPT_GENERATION_CACHE_TTL,
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
        total_chars = len(system_prompt) + len(user_message) + len(llm_response)
        estimated_tokens = total_chars // 4
        cost_per_1k_input = 0.00001
        cost_per_1k_output = 0.00003
        input_cost = estimated_tokens * cost_per_1k_input
        output_tokens = len(llm_response) // 4
        output_cost = output_tokens * cost_per_1k_output
        return round(input_cost + output_cost, 6)

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
    ):
        log_data = {
            "org_id": org_id,
            "query": query[:200],
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

        logger.info(
            f"Script generation {event_type}",
            extra=log_data,
        )
