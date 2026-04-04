"""Knowledge base API endpoints.

Multi-format document ingestion and vector similarity search.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Set

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth_middleware import auth_middleware
from models.knowledge_base import KnowledgeBase, KnowledgeSourceType, KnowledgeStatus
from models.knowledge_chunk import KnowledgeChunk
from schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeChunkResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    DocumentListResponse,
    UploadResponse,
)
from services.ingestion import IngestionService, IngestionError
from services.chunking import SemanticChunkingService
from services.embedding import EmbeddingService
from services.knowledge_base_service import KnowledgeBaseService
from services.tenant_helpers import require_tenant_resource
from sqlalchemy import text

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads")
MAX_FILE_SIZE = 50 * 1024 * 1024
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_ingestion_service: Optional[IngestionService] = None
_chunking_service: Optional[SemanticChunkingService] = None
_kb_service: Optional[KnowledgeBaseService] = None
_embedding_service: Optional[EmbeddingService] = None
_background_tasks: Set[asyncio.Task] = set()


def get_ingestion_service() -> IngestionService:
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service


def get_chunking_service() -> SemanticChunkingService:
    global _chunking_service
    if _chunking_service is None:
        _chunking_service = SemanticChunkingService()
    return _chunking_service


def get_kb_service() -> KnowledgeBaseService:
    global _kb_service
    if _kb_service is None:
        _kb_service = KnowledgeBaseService()
    return _kb_service


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None and OPENAI_API_KEY:
        _embedding_service = EmbeddingService(api_key=OPENAI_API_KEY)
    if _embedding_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service not configured",
        )
    return _embedding_service


@router.post("/upload", response_model=UploadResponse)
async def upload_knowledge(
    file: Optional[UploadFile] = None,
    url: Optional[str] = None,
    text: Optional[str] = None,
    title: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id

    sources_provided = sum([file is not None, url is not None, text is not None])
    if sources_provided != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly one source (file, url, or text) must be provided",
        )

    file_path = None
    try:
        kb_service = get_kb_service()
        ingestion_service = get_ingestion_service()

        if file:
            source_type = KnowledgeSourceType.pdf
            title = title or Path(file.filename).name

            if not ingestion_service.validate_file_format(
                file.filename, file.content_type
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file format: {file.filename}",
                )

            file_path = await _save_uploaded_file(org_id, file)

            extracted_text, metadata = await ingestion_service.extract_pdf(file_path)

        elif url:
            source_type = KnowledgeSourceType.url
            title = title or url

            extracted_text, metadata = await ingestion_service.extract_url(url)

        else:
            source_type = KnowledgeSourceType.text
            title = title or "Text Entry"

            extracted_text = text or ""
            is_valid, error_msg = await ingestion_service.validate_text(
                extracted_text, source_type
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
                )
            metadata = {}

        is_valid, error_msg = await ingestion_service.validate_text(
            extracted_text, source_type
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )

        content_hash = ingestion_service.compute_content_hash(extracted_text)

        existing = await kb_service.get_by_content_hash(session, content_hash, org_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate content already exists in knowledge base",
            )

        kb_data = {
            "title": title,
            "source_type": source_type,
            "source_url": url if source_type == "url" else None,
            "file_path": file_path,
            "content_hash": content_hash,
            "status": KnowledgeStatus.processing,
            "metadata": metadata,
            "org_id": org_id,
        }

        kb = KnowledgeBase.model_validate(kb_data)
        created_kb = await kb_service.create(session, kb)

        task = asyncio.create_task(
            _process_ingestion(
                created_kb.id,
                extracted_text,
                metadata,
                org_id,
                file_path if source_type == KnowledgeSourceType.pdf else None,
            )
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

        logger.info(
            f"Created knowledge base {created_kb.id} for org {org_id}, "
            f"source: {source_type}"
        )

        return UploadResponse(
            knowledge_base_id=created_kb.id,
            status=KnowledgeStatus.processing,
            message="Document uploaded and processing started",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed. Please try again.",
        )


async def _save_uploaded_file(org_id: str, file: UploadFile) -> str:
    tenant_dir = UPLOAD_DIR / org_id
    tenant_dir.mkdir(parents=True, exist_ok=True)

    import uuid

    file_id = str(uuid.uuid4())
    safe_name = Path(file.filename).name
    file_ext = Path(safe_name).suffix
    filename = f"{file_id}{file_ext}"
    file_path = tenant_dir / filename

    total_size = 0
    with open(file_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large (max {MAX_FILE_SIZE} bytes)",
                )
            f.write(chunk)

    return str(file_path)


async def _process_ingestion(
    kb_id: int,
    text: str,
    metadata: dict,
    org_id: str,
    file_path: Optional[str] = None,
):
    session = None
    try:
        from database.session import async_session_maker

        session = async_session_maker()

        await session.execute(
            text("SELECT set_config('app.current_org_id', :org_id, false)"),
            {"org_id": org_id},
        )

        chunking_service = get_chunking_service()
        kb_service = get_kb_service()

        chunks = await chunking_service.chunk_text(text, metadata)

        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")

        embedding_service = get_embedding_service()

        embeddings = await embedding_service.generate_embeddings_batch(chunks)

        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_metadata = chunking_service.enrich_chunk_metadata(
                chunk_text, i, metadata
            )

            await session.execute(
                text("""
                    INSERT INTO knowledge_chunks
                    (org_id, knowledge_base_id, chunk_index, content, embedding, embedding_model, metadata)
                    VALUES (:org_id, :kb_id, :idx, :content, :embedding, :model, :metadata)
                """),
                {
                    "org_id": org_id,
                    "kb_id": kb_id,
                    "idx": i,
                    "content": chunk_text,
                    "embedding": str(embedding),
                    "model": "text-embedding-3-small",
                    "metadata": chunk_metadata,
                },
            )

        await kb_service.update_chunk_count(session, kb_id, len(chunks))

        await session.execute(
            text("""
                UPDATE knowledge_bases
                SET status = 'ready', updated_at = NOW()
                WHERE id = :kb_id
            """),
            {"kb_id": kb_id},
        )

        await session.commit()

        logger.info(
            f"Successfully processed knowledge base {kb_id}: "
            f"{len(chunks)} chunks created"
        )

    except Exception as e:
        logger.error(f"Failed to process knowledge base {kb_id}: {e}")

        if session:
            try:
                await session.execute(
                    text("""
                        UPDATE knowledge_bases
                        SET status = 'failed',
                            error_message = :error_msg,
                            updated_at = NOW()
                        WHERE id = :kb_id
                    """),
                    {"kb_id": kb_id, "error_msg": str(e)[:1000]},
                )
                await session.commit()
            except Exception as commit_error:
                logger.error(
                    f"Failed to mark knowledge base {kb_id} as failed: {commit_error}"
                )

    finally:
        if session:
            await session.close()


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    status_filter: Optional[KnowledgeStatus] = None,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id

    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size

    kb_service = get_kb_service()

    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, false)"),
        {"org_id": org_id},
    )

    if status_filter:
        count_result = await session.execute(
            text(
                "SELECT COUNT(*) FROM knowledge_bases "
                "WHERE status = :status AND soft_delete = false "
                "AND org_id = :org_id"
            ),
            {"status": status_filter, "org_id": org_id},
        )
        total = count_result.scalar() or 0

        items = await kb_service.list_by_status(
            session, status_filter, limit=page_size, offset=offset
        )
    else:
        count_result = await session.execute(
            text(
                "SELECT COUNT(*) FROM knowledge_bases "
                "WHERE soft_delete = false AND org_id = :org_id"
            ),
            {"org_id": org_id},
        )
        total = count_result.scalar() or 0

        items = await kb_service.list_all(session, limit=page_size, offset=offset)

    response_items = [KnowledgeBaseResponse.model_validate(item) for item in items]

    return DocumentListResponse(
        items=response_items, total=total, page=page, page_size=page_size
    )


@router.get("/documents/{document_id}", response_model=KnowledgeBaseResponse)
async def get_document(
    document_id: int,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id

    kb = await require_tenant_resource(
        session, KnowledgeBase, document_id, org_id, "Knowledge Base"
    )

    return KnowledgeBaseResponse.model_validate(kb)


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id

    kb = await require_tenant_resource(
        session, KnowledgeBase, document_id, org_id, "Knowledge Base"
    )

    if kb.status == KnowledgeStatus.processing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete document while processing",
        )

    kb_service = get_kb_service()

    success = await kb_service.mark_soft_deleted(session, document_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    await session.execute(
        text("""
            UPDATE knowledge_chunks
            SET soft_delete = true
            WHERE knowledge_base_id = :kb_id
            AND org_id = :org_id
        """),
        {"kb_id": document_id, "org_id": org_id},
    )
    await session.commit()

    logger.info(f"Soft deleted knowledge base {document_id} for org {org_id}")

    return {"message": "Document deleted successfully"}


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id

    embedding_service = get_embedding_service()
    query_embedding = await embedding_service.generate_embedding(request.query)

    embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

    result = await session.execute(
        text("""
            SELECT
                kc.id as chunk_id,
                kc.knowledge_base_id,
                kc.content,
                kc.metadata,
                1 - (kc.embedding <=> :embedding::vector) as similarity
            FROM knowledge_chunks kc
            JOIN knowledge_bases kb ON kc.knowledge_base_id = kb.id
            WHERE kc.org_id = :org_id
              AND kc.soft_delete = false
              AND kb.soft_delete = false
              AND kb.status = 'ready'
            ORDER BY kc.embedding <=> :embedding::vector
            LIMIT :top_k
        """),
        {"org_id": org_id, "embedding": embedding_str, "top_k": request.top_k},
    )

    rows = result.fetchall()

    results = [
        KnowledgeSearchResult(
            chunk_id=row.chunk_id,
            knowledge_base_id=row.knowledge_base_id,
            content=row.content,
            metadata=row.metadata,
            similarity=float(row.similarity),
        )
        for row in rows
    ]

    return KnowledgeSearchResponse(
        results=results, total=len(results), query=request.query
    )


async def recover_stale_processing_records():
    """Startup sweep: mark stale 'processing' records as 'failed'.

    Called from main.py lifespan to recover from crashes during ingestion.
    """
    from database.session import async_session_maker

    session = async_session_maker()
    try:
        result = await session.execute(
            text("""
                UPDATE knowledge_bases
                SET status = 'failed',
                    error_message = 'Processing interrupted by server restart',
                    updated_at = NOW()
                WHERE status = 'processing'
                  AND updated_at < NOW() - INTERVAL '10 minutes'
            """)
        )
        count = result.rowcount
        await session.commit()
        if count and count > 0:
            logger.info(f"Recovered {count} stale processing records")
    except Exception as e:
        logger.error(f"Failed to recover stale processing records: {e}")
    finally:
        await session.close()
