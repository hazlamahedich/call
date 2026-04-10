import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from models.script_lab_session import ScriptLabSession
from models.script_lab_turn import ScriptLabTurn
from schemas.script_lab import (
    LabChatResponse,
    LabSourceEntry,
    LabSessionResponse,
    SourceAttribution,
)
from schemas.factual_hook import ClaimVerificationResponse
from services.shared_queries import (
    set_rls_context,
    load_agent_for_context,
    load_script_for_context,
    load_lead_for_context,
)

logger = logging.getLogger(__name__)


def _ensure_dict(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    if isinstance(value, dict):
        return value
    return {}


def _ensure_list(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(value, list):
        return value
    return []


class ScriptLabService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_session(
        self,
        org_id: str,
        agent_id: int,
        script_id: int,
        lead_id: int | None = None,
    ) -> LabSessionResponse:
        await load_agent_for_context(self._session, agent_id, org_id)
        await load_script_for_context(self._session, script_id, org_id)
        if lead_id is not None:
            await load_lead_for_context(self._session, lead_id, org_id)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=settings.SCRIPT_LAB_SESSION_TTL_SECONDS)

        lab_session = ScriptLabSession.model_validate(
            {
                "agentId": agent_id,
                "scriptId": script_id,
                "leadId": lead_id,
                "expiresAt": expires_at,
                "status": "active",
                "turnCount": 0,
                "orgId": org_id,
            }
        )
        self._session.add(lab_session)
        await self._session.flush()

        if lab_session.id is None:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "code": "session_create_failed",
                        "message": "Failed to create lab session.",
                    }
                },
            )

        return LabSessionResponse(
            session_id=lab_session.id,
            agent_id=lab_session.agent_id,
            script_id=lab_session.script_id,
            lead_id=lab_session.lead_id,
            status=lab_session.status,
            expires_at=lab_session.expires_at.isoformat(),
            scenario_overlay=lab_session.scenario_overlay,
        )

    async def send_chat_message(
        self,
        org_id: str,
        session_id: int,
        message: str,
        llm_service=None,
        embedding_service=None,
        redis_client=None,
    ) -> LabChatResponse:
        await set_rls_context(self._session, org_id)

        result = await self._session.execute(
            text(
                "SELECT id, org_id, agent_id, script_id, lead_id, "
                "scenario_overlay, expires_at, status, turn_count "
                "FROM script_lab_sessions "
                "WHERE id = :sid AND soft_delete = false "
                "FOR UPDATE"
            ),
            {"sid": session_id},
        )
        row = result.fetchone()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "session_not_found",
                        "message": "Lab session not found",
                    }
                },
            )
        if row[1] != org_id:
            logger.warning(
                "Cross-tenant lab session access attempt",
                extra={
                    "org_id": org_id,
                    "session_owner_org_id": row[1],
                    "session_id": session_id,
                },
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "NAMESPACE_VIOLATION",
                        "message": "Cross-tenant access denied",
                    }
                },
            )

        session_status = row[7]
        if session_status == "expired":
            raise HTTPException(
                status_code=410,
                detail={
                    "error": {
                        "code": "session_expired",
                        "message": "Lab session has expired. Please create a new session.",
                    }
                },
            )

        await self._check_session_expiry(row)

        current_turn_count = row[8]
        if current_turn_count >= settings.SCRIPT_LAB_MAX_TURNS:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": {
                        "code": "max_turns_reached",
                        "message": f"Session has reached the maximum number of turns ({settings.SCRIPT_LAB_MAX_TURNS}). Create a new session.",
                    }
                },
            )

        new_turn_number = current_turn_count + 1

        user_turn = ScriptLabTurn.model_validate(
            {
                "sessionId": session_id,
                "turnNumber": new_turn_number,
                "role": "user",
                "content": message,
                "orgId": org_id,
            }
        )
        self._session.add(user_turn)

        await self._session.execute(
            text(
                "UPDATE script_lab_sessions SET turn_count = turn_count + 1 "
                "WHERE id = :sid"
            ),
            {"sid": session_id},
        )
        await self._session.flush()

        agent_id = row[2]
        script_id = row[3]
        lead_id = row[4]
        scenario_overlay = _ensure_dict(row[5])

        try:
            script = await load_script_for_context(self._session, script_id, org_id)
            render_result = None
            query_text = message

            if settings.VARIABLE_INJECTION_ENABLED:
                from services.variable_injection import VariableInjectionService

                lead_obj = None
                if lead_id is not None:
                    lead_obj = await load_lead_for_context(
                        self._session, lead_id, org_id
                    )

                if scenario_overlay and lead_obj is None:
                    lead_obj = scenario_overlay
                elif scenario_overlay and lead_obj is not None:
                    if isinstance(lead_obj, dict):
                        merged = {**lead_obj, **scenario_overlay}
                    else:
                        merged = {"custom_fields": scenario_overlay}
                        for attr in ("name", "email", "phone", "status"):
                            val = getattr(lead_obj, attr, None)
                            if val:
                                merged[attr] = val
                    lead_obj = merged

                injection_svc = VariableInjectionService(self._session)
                render_result = await injection_svc.render_template(
                    template=script.content,
                    lead=lead_obj,
                )
                query_text = render_result.rendered_text

            from services.script_generation import ScriptGenerationService

            gen_service = ScriptGenerationService(
                llm_service=llm_service,
                embedding_service=embedding_service,
                session=self._session,
                redis_client=redis_client,
            )

            gen_result = await gen_service.generate_response(
                query=query_text,
                org_id=org_id,
                agent_id=agent_id,
                grounding_mode="strict",
            )

            source_attributions = self._format_source_attribution(
                gen_result.source_chunks
            )
            grounding_confidence = gen_result.grounding_confidence
            low_confidence_warning = grounding_confidence < 0.5
            response_text = gen_result.response
            was_corrected = getattr(gen_result, "was_corrected", False)
            correction_count = getattr(gen_result, "correction_count", 0)
            verification_timed_out = getattr(
                gen_result, "verification_timed_out", False
            )
            verified_claims_raw = getattr(gen_result, "verified_claims", [])

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "LLM/RAG pipeline failed during lab chat",
                extra={
                    "session_id": session_id,
                    "org_id": org_id,
                    "error": str(e),
                },
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "code": "generation_failed",
                        "message": "Failed to generate response. Please try again.",
                    }
                },
            )

        assistant_turn_number = new_turn_number + 1
        attribution_data = [
            {
                "chunk_id": sa.chunk_id,
                "document_name": sa.document_name,
                "page_number": sa.page_number,
                "excerpt": sa.excerpt,
                "similarity_score": sa.similarity_score,
            }
            for sa in source_attributions
        ]

        try:
            assistant_turn = ScriptLabTurn.model_validate(
                {
                    "sessionId": session_id,
                    "turnNumber": assistant_turn_number,
                    "role": "assistant",
                    "content": response_text,
                    "sourceAttributions": attribution_data,
                    "groundingConfidence": grounding_confidence,
                    "lowConfidenceWarning": low_confidence_warning,
                    "correctionCount": correction_count,
                    "wasCorrected": was_corrected,
                    "orgId": org_id,
                }
            )
            self._session.add(assistant_turn)
            await self._session.flush()
        except Exception as e:
            logger.error(
                "Failed to persist assistant turn (orphaned)",
                extra={
                    "session_id": session_id,
                    "turn_number": assistant_turn_number,
                    "error": str(e),
                },
            )

        await self._session.execute(
            text(
                "UPDATE script_lab_sessions SET turn_count = turn_count + 1 "
                "WHERE id = :sid"
            ),
            {"sid": session_id},
        )
        await self._session.flush()

        verified_claim_responses = [
            ClaimVerificationResponse(
                claim_text=vc.claim_text,
                is_supported=vc.is_supported,
                max_similarity=vc.max_similarity,
                verification_error=vc.verification_error,
            )
            for vc in verified_claims_raw
        ]

        return LabChatResponse(
            response_text=response_text,
            source_attributions=source_attributions,
            grounding_confidence=grounding_confidence,
            turn_number=new_turn_number,
            low_confidence_warning=low_confidence_warning,
            was_corrected=was_corrected,
            correction_count=correction_count,
            verification_timed_out=verification_timed_out,
            verified_claims=verified_claim_responses,
        )

    async def set_scenario_overlay(
        self,
        org_id: str,
        session_id: int,
        overlay: dict[str, str],
    ) -> LabSessionResponse:
        result = await self._session.execute(
            text(
                "SELECT id, org_id, agent_id, script_id, lead_id, "
                "status, expires_at, scenario_overlay "
                "FROM script_lab_sessions "
                "WHERE id = :sid AND soft_delete = false"
            ),
            {"sid": session_id},
        )
        row = result.fetchone()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "session_not_found",
                        "message": "Lab session not found",
                    }
                },
            )
        if row[1] != org_id:
            logger.warning(
                "Cross-tenant overlay access attempt",
                extra={
                    "org_id": org_id,
                    "session_owner_org_id": row[1],
                    "session_id": session_id,
                },
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "NAMESPACE_VIOLATION",
                        "message": "Cross-tenant access denied",
                    }
                },
            )

        if row[5] == "expired":
            raise HTTPException(
                status_code=410,
                detail={
                    "error": {
                        "code": "session_expired",
                        "message": "Lab session has expired. Please create a new session.",
                    }
                },
            )

        expires_at = row[6]
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= expires_at:
                raise HTTPException(
                    status_code=410,
                    detail={
                        "error": {
                            "code": "session_expired",
                            "message": "Lab session has expired. Please create a new session.",
                        }
                    },
                )

        from services.variable_injection import VariableInjectionService

        sanitized = {}
        for k, v in overlay.items():
            sanitized[k] = VariableInjectionService._sanitize_value(v)

        await self._session.execute(
            text(
                "UPDATE script_lab_sessions SET scenario_overlay = :overlay "
                "WHERE id = :sid AND org_id = :org_id AND soft_delete = false "
                "AND status = 'active' AND expires_at > NOW()"
            ),
            {"overlay": sanitized, "sid": session_id, "org_id": org_id},
        )
        await self._session.flush()

        refreshed = await self._session.execute(
            text(
                "SELECT id, org_id, agent_id, script_id, lead_id, "
                "status, expires_at, scenario_overlay "
                "FROM script_lab_sessions "
                "WHERE id = :sid AND soft_delete = false"
            ),
            {"sid": session_id},
        )
        fresh_row = refreshed.fetchone()
        if fresh_row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "session_not_found",
                        "message": "Lab session not found after update.",
                    }
                },
            )

        return LabSessionResponse(
            session_id=fresh_row[0],
            agent_id=fresh_row[2],
            script_id=fresh_row[3],
            lead_id=fresh_row[4],
            status=fresh_row[5],
            expires_at=fresh_row[6].isoformat() if fresh_row[6] else "",
            scenario_overlay=_ensure_dict(fresh_row[7]),
        )

    async def get_session_sources(
        self,
        org_id: str,
        session_id: int,
    ) -> list[LabSourceEntry]:
        ownership = await self._session.execute(
            text(
                "SELECT org_id FROM script_lab_sessions "
                "WHERE id = :sid AND soft_delete = false"
            ),
            {"sid": session_id},
        )
        owner_row = ownership.fetchone()
        if owner_row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "session_not_found",
                        "message": "Lab session not found",
                    }
                },
            )
        if owner_row[0] != org_id:
            logger.warning(
                "Cross-tenant source log access attempt",
                extra={
                    "org_id": org_id,
                    "session_owner_org_id": owner_row[0],
                    "session_id": session_id,
                },
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "NAMESPACE_VIOLATION",
                        "message": "Cross-tenant access denied",
                    }
                },
            )

        turns = await self._session.execute(
            text(
                "SELECT turn_number, role, content, source_attributions, "
                "grounding_confidence "
                "FROM script_lab_turns "
                "WHERE session_id = :sid AND soft_delete = false "
                "ORDER BY turn_number ASC"
            ),
            {"sid": session_id},
        )
        rows = turns.fetchall()

        entries: list[LabSourceEntry] = []
        user_turns: dict[int, str] = {}
        assistant_turns: dict[int, dict] = {}

        for row in rows:
            turn_number = row[0]
            role = row[1]
            content = row[2]
            if role == "user":
                user_turns[turn_number] = content
            elif role == "assistant":
                raw_attributions = _ensure_list(row[3])
                assistant_turns[turn_number] = {
                    "content": content,
                    "source_attributions": raw_attributions,
                    "grounding_confidence": row[4] if row[4] is not None else 0.0,
                }

        for turn_num in sorted(assistant_turns.keys()):
            a = assistant_turns[turn_num]
            candidate_user = turn_num - 1
            user_msg = user_turns.get(candidate_user, "")
            sources = [
                SourceAttribution(
                    chunk_id=s.get("chunk_id", 0),
                    document_name=s.get("document_name", "Unknown Document"),
                    page_number=s.get("page_number"),
                    excerpt=s.get("excerpt", ""),
                    similarity_score=s.get("similarity_score", 0.0),
                )
                for s in a["source_attributions"]
            ]
            display_turn = (turn_num + 1) // 2
            entries.append(
                LabSourceEntry(
                    turn_number=display_turn,
                    user_message=user_msg,
                    ai_response=a["content"],
                    sources=sources,
                    grounding_confidence=a["grounding_confidence"],
                )
            )

        return entries

    async def delete_session(
        self,
        org_id: str,
        session_id: int,
    ) -> None:
        ownership = await self._session.execute(
            text(
                "SELECT org_id FROM script_lab_sessions "
                "WHERE id = :sid AND soft_delete = false"
            ),
            {"sid": session_id},
        )
        owner_row = ownership.fetchone()
        if owner_row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "session_not_found",
                        "message": "Lab session not found",
                    }
                },
            )
        if owner_row[0] != org_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "NAMESPACE_VIOLATION",
                        "message": "Cross-tenant access denied",
                    }
                },
            )

        await self._session.execute(
            text(
                "UPDATE script_lab_sessions SET soft_delete = true WHERE id = :sid AND org_id = :org_id"
            ),
            {"sid": session_id, "org_id": org_id},
        )
        await self._session.execute(
            text(
                "UPDATE script_lab_turns SET soft_delete = true WHERE session_id = :sid AND org_id = :org_id"
            ),
            {"sid": session_id, "org_id": org_id},
        )
        await self._session.flush()

    async def _check_session_expiry(self, session_row) -> None:
        expires_at = session_row[6]
        if expires_at is None:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "code": "invalid_session",
                        "message": "Session has no expiry set.",
                    }
                },
            )
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if now >= expires_at:
            await self._session.execute(
                text(
                    "UPDATE script_lab_sessions SET status = 'expired' WHERE id = :sid AND org_id = :org_id"
                ),
                {"sid": session_row[0], "org_id": session_row[1]},
            )
            await self._session.flush()
            raise HTTPException(
                status_code=410,
                detail={
                    "error": {
                        "code": "session_expired",
                        "message": "Lab session has expired. Please create a new session.",
                    }
                },
            )

    async def cleanup_expired_sessions(self) -> int:
        result = await self._session.execute(
            text(
                "UPDATE script_lab_sessions SET status = 'expired' "
                "WHERE expires_at < NOW() AND status = 'active' "
                "AND soft_delete = false"
            )
        )
        count = result.rowcount
        if count > 0:
            await self._session.commit()
            logger.info(
                "Cleaned up %d expired lab sessions",
                count,
            )
        return count

    def _format_source_attribution(
        self,
        chunks: list[dict] | None,
    ) -> list[SourceAttribution]:
        if not chunks:
            return []

        attributions: list[SourceAttribution] = []
        for chunk in chunks:
            metadata = chunk.get("metadata") or {}
            document_name = metadata.get("source_file", "Unknown Document")
            page_number = metadata.get("page_number")
            content = chunk.get("content", "")
            excerpt = content[:200] if content else ""
            similarity = chunk.get("similarity", 0.0)
            chunk_id = chunk.get("chunk_id", 0)

            attributions.append(
                SourceAttribution(
                    chunk_id=chunk_id,
                    document_name=document_name,
                    page_number=page_number,
                    excerpt=excerpt,
                    similarity_score=round(similarity, 4),
                )
            )
        return attributions
