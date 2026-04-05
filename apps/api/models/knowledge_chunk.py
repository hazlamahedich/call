"""Knowledge Chunk model for vector-embedded text segments.

Stores semantic chunks of knowledge base documents with vector embeddings
for similarity search. Chunks are tenant-isolated and linked to parent
knowledge base documents.
"""

from datetime import datetime, timezone
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlmodel import Field, ForeignKey, SQLModel

from config.settings import settings
from models.base import TenantModel


class KnowledgeChunk(TenantModel, table=True):
    """Vector-embedded text chunk for RAG retrieval.

    Each chunk represents a semantic segment of a knowledge base document
    with its vector embedding for similarity search.
    """

    __tablename__ = "knowledge_chunks"  # type: ignore

    knowledge_base_id: Optional[int] = Field(
        default=None,
        foreign_key="knowledge_bases.id",
        index=True,
        description="Parent knowledge base document ID",
    )
    chunk_index: int = Field(description="Order of this chunk within the document")
    content: str = Field(
        description="Chunk text content (unlimited length for 1000-token chunks)"
    )
    embedding: Vector = Field(
        dimension=settings.AI_EMBEDDING_DIMENSIONS,
        description="Vector embedding (configurable dimensions)",
    )
    embedding_model: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Embedding model used (for future migration)",
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Chunk metadata (page number, section, etc.)",
    )
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
