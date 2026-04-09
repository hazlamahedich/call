import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings

logger = logging.getLogger(__name__)


async def _invalidate_script_gen_cache(org_id: str):
    try:
        import redis.asyncio as aioredis

        redis = aioredis.from_url(settings.REDIS_URL)
        try:
            keys = [k async for k in redis.scan_iter(match=f"script_gen:{org_id}:*")]
            if keys:
                await redis.delete(*keys)
        finally:
            await redis.close()
    except Exception as e:
        logger.warning("Script gen cache invalidation failed for org %s: %s", org_id, e)


async def search_knowledge_chunks(
    session: AsyncSession,
    query_embedding: list[float],
    org_id: str,
    max_chunks: int = 5,
    threshold: float = settings.RAG_SIMILARITY_THRESHOLD,
    knowledge_base_ids: list[int] | None = None,
) -> list[dict]:
    kb_filter = ""
    params: dict = {
        "query_embedding": str(query_embedding),
        "org_id": org_id,
        "max_chunks": max_chunks,
        "threshold": threshold,
    }
    if knowledge_base_ids:
        kb_filter = "AND kc.knowledge_base_id = ANY(:kb_ids) "
        params["kb_ids"] = knowledge_base_ids

    result = await session.execute(
        text(
            "SELECT kc.id, kc.knowledge_base_id, kc.content, kc.metadata, "
            "1 - (kc.embedding <=> :query_embedding::vector) AS similarity "
            "FROM knowledge_chunks kc "
            "JOIN knowledge_bases kb ON kc.knowledge_base_id = kb.id "
            "WHERE kc.org_id = :org_id "
            "AND kc.soft_delete = false "
            "AND kb.status = 'ready' "
            "AND kb.soft_delete = false "
            f"{kb_filter}"
            "AND 1 - (kc.embedding <=> :query_embedding::vector) > :threshold "
            "ORDER BY kc.embedding <=> :query_embedding::vector "
            "LIMIT :max_chunks"
        ),
        params,
    )
    return [
        {
            "chunk_id": row[0],
            "knowledge_base_id": row[1],
            "content": row[2],
            "metadata": row[3],
            "similarity": float(row[4]),
        }
        for row in result.fetchall()
    ]
