"""Knowledge Base Service for CRUD operations.

Extends TenantService with custom methods for knowledge base management.
Follows the pattern established by voice presets.
"""

from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.knowledge_base import KnowledgeBase, KnowledgeStatus
from services.base import TenantService


class KnowledgeBaseService(TenantService[KnowledgeBase]):
    """Service for knowledge base CRUD operations.

    Extends TenantService with custom methods for content hash lookup,
    status filtering, and failure marking.
    """

    def __init__(self):
        super().__init__(KnowledgeBase)

    async def get_by_content_hash(
        self, session: AsyncSession, content_hash: str, org_id: str
    ) -> Optional[KnowledgeBase]:
        """Get a knowledge base document by content hash.

        Used for deduplication detection before ingestion.

        Args:
            session: Database session
            content_hash: SHA-256 hash to look up
            org_id: Tenant organization ID for scope

        Returns:
            KnowledgeBase if found, None otherwise
        """
        stmt = text(
            f"SELECT {self._select_cols} FROM {self.table_name} "
            "WHERE content_hash = :content_hash "
            "AND org_id = :org_id "
            "AND soft_delete = false"
        )
        result = await session.execute(
            stmt.bindparams(content_hash=content_hash, org_id=org_id)
        )
        row = result.first()
        if row is None:
            return None
        return self._row_to_instance(row)

    async def list_by_status(
        self,
        session: AsyncSession,
        status: KnowledgeStatus,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KnowledgeBase]:
        """List knowledge base documents by status.

        Args:
            session: Database session
            status: Status filter (processing, ready, or failed)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of knowledge base documents
        """
        await self._ensure_tenant_context(session)
        stmt = text(
            f"SELECT {self._select_cols} FROM {self.table_name} "
            "WHERE status = :status "
            "AND soft_delete = false "
            "ORDER BY "
            "CASE status WHEN 'ready' THEN 1 WHEN 'processing' THEN 2 ELSE 3 END, "
            "created_at DESC "
            "LIMIT :lim OFFSET :off"
        )
        result = await session.execute(
            stmt.bindparams(status=status, lim=limit, off=offset)
        )
        rows = result.fetchall()
        return [self._row_to_instance(row) for row in rows]

    async def mark_failed(
        self,
        session: AsyncSession,
        record_id: int,
        error_message: str,
    ) -> bool:
        """Mark a knowledge base document as failed.

        Args:
            session: Database session
            record_id: Document ID
            error_message: Specific error message

        Returns:
            True if updated, False if not found
        """
        stmt = text(
            f"UPDATE {self.table_name} "
            "SET status = 'failed', "
            "error_message = :error_message, "
            "updated_at = NOW() "
            "WHERE id = :record_id "
            "AND (soft_delete = false OR soft_delete IS NULL)"
        )
        result = await session.execute(
            stmt.bindparams(record_id=record_id, error_message=error_message)
        )
        await session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]

    async def update_chunk_count(
        self,
        session: AsyncSession,
        record_id: int,
        chunk_count: int,
    ) -> bool:
        """Update the chunk count for a knowledge base document.

        Args:
            session: Database session
            record_id: Document ID
            chunk_count: New chunk count

        Returns:
            True if updated, False if not found
        """
        stmt = text(
            f"UPDATE {self.table_name} "
            "SET chunk_count = :chunk_count, "
            "updated_at = NOW() "
            "WHERE id = :record_id "
            "AND (soft_delete = false OR soft_delete IS NULL)"
        )
        result = await session.execute(
            stmt.bindparams(record_id=record_id, chunk_count=chunk_count)
        )
        await session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]
