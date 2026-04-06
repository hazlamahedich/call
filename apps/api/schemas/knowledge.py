"""Knowledge base request and response schemas.

Pydantic models for knowledge base API endpoints with camelCase aliases.
"""

from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, AliasGenerator, Field
from pydantic.alias_generators import to_camel

from models.knowledge_base import KnowledgeSourceType, KnowledgeStatus


class KnowledgeBaseCreate(BaseModel):
    """Request schema for creating a knowledge base document."""

    title: str = Field(..., max_length=200, description="Document name or title")
    source_type: KnowledgeSourceType = Field(..., description="Source type")
    source_url: Optional[str] = Field(None, max_length=2048, description="Source URL")
    text: Optional[str] = Field(None, description="Raw text content")

    class Config:
        alias_generator = AliasGenerator(to_camel)
        populate_by_name = True


class KnowledgeBaseResponse(BaseModel):
    """Response schema for knowledge base document."""

    id: int
    orgId: str = Field(alias="org_id")
    title: str
    sourceType: KnowledgeSourceType = Field(alias="source_type")
    sourceUrl: Optional[str] = Field(None, alias="source_url")
    filePath: Optional[str] = Field(None, alias="file_path")
    fileStorageUrl: Optional[str] = Field(None, alias="file_storage_url")
    contentHash: Optional[str] = Field(None, alias="content_hash")
    chunkCount: int = Field(alias="chunk_count")
    status: KnowledgeStatus
    errorMessage: Optional[str] = Field(None, alias="error_message")
    metadata: Optional[dict] = None
    createdAt: Optional[datetime] = Field(None, alias="created_at")
    updatedAt: Optional[datetime] = Field(None, alias="updated_at")

    class Config:
        alias_generator = AliasGenerator(to_camel)
        populate_by_name = True
        from_attributes = True


class KnowledgeChunkResponse(BaseModel):
    """Response schema for knowledge chunk."""

    id: int
    orgId: str = Field(alias="org_id")
    knowledgeBaseId: int = Field(alias="knowledge_base_id")
    chunkIndex: int = Field(alias="chunk_index")
    content: str
    metadata: Optional[dict] = None
    createdAt: datetime = Field(alias="created_at")

    class Config:
        alias_generator = AliasGenerator(to_camel)
        populate_by_name = True
        from_attributes = True


class KnowledgeSearchRequest(BaseModel):
    """Request schema for knowledge base search."""

    query: str = Field(..., min_length=1, description="Search query")
    topK: int = Field(
        default=5, ge=1, le=20, alias="top_k", description="Number of results"
    )

    class Config:
        alias_generator = AliasGenerator(to_camel)
        populate_by_name = True


class KnowledgeSearchResult(BaseModel):
    """Single search result with similarity score."""

    chunkId: int = Field(alias="chunk_id")
    knowledgeBaseId: int = Field(alias="knowledge_base_id")
    content: str
    metadata: Optional[dict] = None
    similarity: float = Field(description="Cosine similarity score (0-1)")

    class Config:
        alias_generator = AliasGenerator(to_camel)
        populate_by_name = True


class KnowledgeSearchResponse(BaseModel):
    """Response schema for knowledge base search."""

    results: List[KnowledgeSearchResult]
    total: int
    query: str

    class Config:
        alias_generator = AliasGenerator(to_camel)
        populate_by_name = True


class DocumentListResponse(BaseModel):
    """Response schema for paginated document list."""

    items: List[KnowledgeBaseResponse]
    total: int
    page: int
    pageSize: int = Field(alias="page_size")

    class Config:
        alias_generator = AliasGenerator(to_camel)
        populate_by_name = True


class UploadResponse(BaseModel):
    """Response schema for file upload."""

    knowledgeBaseId: int = Field(alias="knowledge_base_id")
    status: KnowledgeStatus
    message: str = "Document uploaded successfully"

    class Config:
        alias_generator = AliasGenerator(to_camel)
        populate_by_name = True


class RetryResponse(BaseModel):
    """Response schema for document retry."""

    knowledgeBaseId: int = Field(alias="knowledge_base_id")
    status: KnowledgeStatus
    message: str = "Document retry initiated"

    class Config:
        alias_generator = AliasGenerator(to_camel)
        populate_by_name = True


class NamespaceError(BaseModel):
    code: Literal["NAMESPACE_VIOLATION"] = "NAMESPACE_VIOLATION"
    message: str = "Cross-tenant access denied"
    timestamp: str


class NamespaceViolationResponse(BaseModel):
    error: NamespaceError
