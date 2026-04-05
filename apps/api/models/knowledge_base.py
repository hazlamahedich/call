"""Knowledge Base model for multi-format document ingestion.

Stores metadata about uploaded documents (PDFs, URLs, text) and their
ingestion status. All knowledge bases are tenant-isolated by org_id.
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from sqlmodel import Field, SQLModel

from models.base import TenantModel

KnowledgeSourceType = Literal["pdf", "url", "text", "markdown"]
KnowledgeStatus = Literal["processing", "ready", "failed"]


class KnowledgeBase(TenantModel, table=True):
    """Knowledge base document for multi-format content ingestion.

    Each document is processed asynchronously: text is extracted, chunked
    semantically, and converted to vector embeddings for RAG retrieval.
    """

    __tablename__ = "knowledge_bases"  # type: ignore

    title: str = Field(max_length=200, description="Document name or title")
    source_type: KnowledgeSourceType = Field(
        description="Source type: pdf, url, or text"
    )
    source_url: Optional[str] = Field(
        default=None, max_length=2048, description="Original URL for URL-type sources"
    )
    file_path: Optional[str] = Field(
        default=None, max_length=512, description="Storage path for uploaded files"
    )
    file_storage_url: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Tenant-scoped storage URL for uploaded files",
    )
    content_hash: Optional[str] = Field(
        default=None,
        max_length=64,
        index=True,
        description="SHA-256 hash for deduplication",
    )
    chunk_count: int = Field(
        default=0, description="Number of chunks created from this document"
    )
    status: KnowledgeStatus = Field(
        default="processing",
        description="Ingestion status: processing, ready, or failed",
    )
    error_message: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Specific error message if status is failed",
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Additional metadata (pages, word count, etc.)",
    )
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
