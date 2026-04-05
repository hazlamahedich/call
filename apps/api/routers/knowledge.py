"""Knowledge base API endpoints.

Multi-format document ingestion with vector similarity search.
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database.session import AsyncSessionLocal, get_session as get_db
from middleware.auth_middleware import auth_middleware
from models.knowledge_base import KnowledgeBase, KnowledgeSourceType, KnowledgeStatus
from models.knowledge_chunk import KnowledgeChunk
from schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeChunkResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    DocumentListResponse,
    UploadResponse,
    RetryResponse,
)
from services.ingestion import IngestionService, IngestionError
from services.chunking import SemanticChunkingService
from services.embedding import (
    EmbeddingService,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    MAX_BATCH_SIZE,
)
from services.knowledge_base_service import KnowledgeBaseService
from services.tenant_helpers import require_tenant_resource

from middleware.rate_limit import knowledge_upload_limiter

from config.settings import settings

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads")
MAX_FILE_SIZE = 50 * 1024 * 1024
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BACKGROUND_TASK_TIMEOUT = 30 * 60
MAX_BACKGROUND_TASKS = 10
STALE_THRESHOLD_MINUTES = 30

router = APIRouter(tags=["Knowledge Base"])

_ingestion_service: Optional[IngestionService] = None
_chunking_service: Optional[SemanticChunkingService] = None
_kb_service: Optional[KnowledgeBaseService] = None
_embedding_service: Optional[EmbeddingService] = None
_background_tasks: set[asyncio.Task] = set()


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


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None and OPENAI_API_KEY:
        _embedding_service = EmbeddingService(api_key=OPENAI_API_KEY)
    if _embedding_service is None:
        raise RuntimeError("Embedding service not configured")
    return _embedding_service


def get_kb_service() -> KnowledgeBaseService:
    global _kb_service
    if _kb_service is None:
        _kb_service = KnowledgeBaseService()
    return _kb_service


async def _set_rls_context(session: AsyncSession, org_id: str):
    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, false)"),
        {"org_id": org_id},
    )


async def _set_admin_context(session: AsyncSession, org_id: str):
    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, false)"),
        {"org_id": org_id},
    )
    await session.execute(
        text("SELECT set_config('app.is_platform_admin', 'true', false)"),
    )


async def _process_ingestion(
    kb_id: int,
    extracted_text: str,
    metadata: dict,
    org_id: str,
    source_type: str,
    file_path: Optional[str] = None,
) -> None:
    session = None
    try:
        session = AsyncSessionLocal()
        await _set_rls_context(session, org_id)

        chunking_service = get_chunking_service()
        embedding_service = get_embedding_service()
        kb_service = get_kb_service()

        chunks = await chunking_service.chunk_text(extracted_text, metadata)
        if not chunks:
            raise IngestionError("No chunks produced from document", "NO_CHUNKS")

        chunk_meta_list = []
        for i, chunk in enumerate(chunks):
            chunk_meta = chunking_service.enrich_chunk_metadata(chunk, i, metadata)
            chunk_meta["embedding_model"] = EMBEDDING_MODEL
            chunk_meta["source_type"] = source_type
            if source_type == "pdf" and "page" in metadata:
                chunk_meta["page"] = metadata["page"]
            chunk_meta_list.append(chunk_meta)

        all_embeddings = []
        for batch_start in range(0, len(chunks), MAX_BATCH_SIZE):
            batch_texts = chunks[batch_start : batch_start + MAX_BATCH_SIZE]
            batch_embeddings = await embedding_service.generate_embeddings_batch(
                batch_texts
            )
            for emb in batch_embeddings:
                if len(emb) != EMBEDDING_DIMENSIONS:
                    raise ValueError(
                        f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {len(emb)}"
                    )
            all_embeddings.extend(batch_embeddings)

        inserted_count = 0
        for i, (chunk_text, embedding) in enumerate(zip(chunks, all_embeddings)):
            chunk_meta = chunk_meta_list[i]
            await session.execute(
                text(
                    "INSERT INTO knowledge_chunks "
                    "(org_id, knowledge_base_id, chunk_index, content, embedding, "
                    " embedding_model, metadata, created_at) "
                    "VALUES (:org_id, :kb_id, :chunk_index, :content, :embedding, "
                    " :embedding_model, CAST(:metadata AS jsonb), NOW())"
                ),
                {
                    "org_id": org_id,
                    "kb_id": kb_id,
                    "chunk_index": i,
                    "content": chunk_text,
                    "embedding": str(embedding),
                    "embedding_model": EMBEDDING_MODEL,
                    "metadata": str(chunk_meta) if chunk_meta else None,
                },
            )
            inserted_count += 1

        await kb_service.update_chunk_count(session, kb_id, len(all_embeddings))

        await session.execute(
            text(
                "UPDATE knowledge_bases "
                "SET status = 'ready', chunk_count = :chunk_count, updated_at = NOW() "
                "WHERE id = :kb_id AND org_id = :org_id"
            ),
            {"kb_id": kb_id, "chunk_count": len(all_embeddings), "org_id": org_id},
        )
        await session.commit()

        logger.info(
            "Knowledge base %d processed for org %s: %d chunks, processing->ready",
            kb_id,
            org_id,
            len(chunks),
            extra={
                "org_id": org_id,
                "source_type": source_type,
                "chunk_count": len(chunks),
                "transition": "processing->ready",
            },
        )

        if file_path:
            try:
                Path(file_path).unlink(missing_ok=True)
                logger.info("Cleaned up uploaded file: %s", file_path)
            except Exception:
                logger.warning("Failed to clean up file %s", file_path)

    except Exception as e:
        logger.error(
            "Failed to process knowledge base %d for org %s: %s", kb_id, org_id, e
        )
        if session:
            try:
                await session.execute(
                    text(
                        "DELETE FROM knowledge_chunks WHERE knowledge_base_id = :kb_id AND org_id = :org_id"
                    ),
                    {"kb_id": kb_id, "org_id": org_id},
                )
                await session.execute(
                    text("SELECT set_config('app.current_org_id', :org_id, false)"),
                    {"org_id": org_id},
                )
                await session.execute(
                    text(
                        "UPDATE knowledge_bases "
                        "SET status = 'failed', error_message = :error_msg, updated_at = NOW() "
                        "WHERE id = :kb_id AND org_id = :org_id"
                    ),
                    {"kb_id": kb_id, "error_msg": str(e)[:1000], "org_id": org_id},
                )
                await session.commit()
            except Exception as inner_e:
                logger.error("Failed to cleanup chunks for kb %d: %s", kb_id, inner_e)
    finally:
        if session:
            await session.close()


async def recover_stale_processing_records():
    try:
        session = AsyncSessionLocal()
        try:
            result = await session.execute(
                text(
                    "UPDATE knowledge_bases "
                    "SET status = 'failed', error_message = 'Recovery: stale processing record', updated_at = NOW() "
                    "WHERE status = 'processing' "
                    "AND updated_at < NOW() - INTERVAL '%s minutes' "
                    "RETURNING id, org_id"
                )
                % STALE_THRESHOLD_MINUTES
            )
            rows = result.fetchall()
            if rows:
                await session.execute(
                    text("SELECT set_config('app.is_platform_admin', 'true', false)")
                )
                await session.commit()
                logger.info("Recovered %d stale processing records", len(rows))
            else:
                await session.commit()
        finally:
            await session.close()
    except Exception as e:
        logger.error("Knowledge base recovery failed: %s", e)


def _cleanup_file(file_path: str):
    try:
        Path(file_path).unlink(missing_ok=True)
        logger.info("Cleaned up uploaded file: %s", file_path)
    except Exception:
        logger.warning("Failed to clean up file: %s", file_path)


def _validate_org_id(org_id: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-_]+$", org_id))


async def _save_uploaded_file(org_id: str, file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is required for upload",
        )
    if not _validate_org_id(org_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid org_id format",
        )

    tenant_dir = UPLOAD_DIR / org_id
    tenant_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(__import__("uuid").uuid4())
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
                f.close()
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large (max {MAX_FILE_SIZE} bytes)",
                )
            f.write(chunk)

    return str(file_path)


async def _extract_text_from_file(
    ingestion_service: IngestionService,
    file_path: str,
    filename: str,
) -> tuple[str, dict]:
    file_ext = Path(filename).suffix.lower()
    if file_ext == ".pdf":
        return await ingestion_service.extract_pdf(file_path)
    elif file_ext in (".txt", ".md"):
        path = Path(file_path)
        text = path.read_text(encoding="utf-8", errors="replace")
        metadata = {
            "page_count": 1,
            "word_count": len(text.split()),
            "extraction_method": "plain_text",
            "source_format": file_ext.lstrip("."),
        }
        return text, metadata
    else:
        raise IngestionError(
            f"Unsupported file format: {file_ext}", "UNSUPPORTED_FORMAT"
        )


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
    if not _validate_org_id(org_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid org_id format",
        )

    if len(_background_tasks) >= MAX_BACKGROUND_TASKS:
        raise HTTPException(
            status_code=503,
            detail="Too many concurrent uploads, please try again later",
        )

    allowed = await knowledge_upload_limiter.check_rate_limit(org_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Upload rate limit exceeded, please try again later",
        )

    await _set_rls_context(session, org_id)

    sources_provided = sum([file is not None, url is not None, text is not None])
    if sources_provided != 1:
        raise HTTPException(
            status_code=400,
            detail="Exactly one source (file, url, or text) must be provided",
        )

    ingestion_service = get_ingestion_service()
    kb_service = get_kb_service()

    extracted_text = ""
    metadata = {}
    source_type = KnowledgeSourceType.pdf
    file_path = None

    if file:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="File name is required",
            )
        if not ingestion_service.validate_file_format(file.filename, file.content_type):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file.filename}",
            )
        title = title or Path(file.filename).name
        file_path = await _save_uploaded_file(org_id, file)
        try:
            extracted_text, metadata = await _extract_text_from_file(
                ingestion_service, file_path, file.filename
            )
        except IngestionError as exc:
            _cleanup_file(file_path)
            raise HTTPException(status_code=400, detail=str(exc))
    elif url:
        source_type = KnowledgeSourceType.url
        if not url.strip():
            raise HTTPException(
                status_code=400,
                detail="URL is required",
            )
        if not ingestion_service._is_valid_url(url):
            raise HTTPException(
                status_code=400,
                detail="Invalid URL format",
            )
        title = title or url
        try:
            extracted_text, metadata = await ingestion_service.extract_url(url)
        except IngestionError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    elif text:
        source_type = KnowledgeSourceType.text
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Text is required",
            )
        if len(text.strip()) < 100:
            raise HTTPException(
                status_code=400,
                detail="Text content too short (minimum 100 characters)",
            )
        extracted_text = text
        metadata = {}
    else:
        raise HTTPException(
            status_code=400,
            detail="No valid source provided",
        )

    is_valid, error_msg = await ingestion_service.validate_text(
        extracted_text, source_type
    )
    if not is_valid:
        if file_path:
            _cleanup_file(file_path)
        raise HTTPException(
            status_code=400,
            detail=error_msg or "Invalid content",
        )

    content_hash = ingestion_service.compute_content_hash(extracted_text)
    existing = await kb_service.get_by_content_hash(session, content_hash, org_id)
    if existing:
        if file_path:
            _cleanup_file(file_path)
        raise HTTPException(
            status_code=409,
            detail="Duplicate content already exists in knowledge base",
        )

    kb_data = {
        "title": title,
        "source_type": source_type,
        "source_url": url if source_type == "url" else None,
        "file_path": str(file_path) if file_path else None,
        "file_storage_url": str(file_path) if file_path else None,
        "content_hash": content_hash,
        "status": KnowledgeStatus.processing,
        "metadata": metadata,
        "org_id": org_id,
    }
    kb = KnowledgeBase.model_validate(kb_data)
    created_kb = await kb_service.create(session, kb)
    await session.commit()

    task = asyncio.create_task(
        _process_ingestion(
            created_kb.id,
            extracted_text,
            metadata,
            org_id,
            source_type,
            file_path if source_type in ("pdf",) else None,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    logger.info(
        "Created knowledge base %d for org %s",
        created_kb.id,
        org_id,
        extra={
            "org_id": org_id,
            "source_type": source_type,
            "transition": "created->processing",
        },
    )

    return UploadResponse(
        knowledge_base_id=created_kb.id,
        status=KnowledgeStatus.processing,
        message="Document uploaded successfully",
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id
    await _set_rls_context(session, org_id)

    kb_service = get_kb_service()

    offset = (page - 1) * page_size
    stmt = text(
        "SELECT id, org_id, title, source_type, source_url, file_path, file_storage_url, "
        "content_hash, chunk_count, status, error_message, metadata, created_at, updated_at, soft_delete "
        "FROM knowledge_bases "
        "WHERE soft_delete = false "
    )
    params = {"lim": page_size, "off": offset}

    if status_filter:
        stmt = text(
            str(stmt) + "AND status = :status_filter "
            "ORDER BY "
            "CASE status WHEN 'ready' THEN 1 WHEN 'processing' THEN 2 ELSE 3 END, "
            "created_at DESC "
            "LIMIT :lim OFFSET :off"
        )
        params["status_filter"] = status_filter
    else:
        stmt = text(
            str(stmt) + "ORDER BY "
            "CASE status WHEN 'ready' THEN 1 WHEN 'processing' THEN 2 ELSE 3 END, "
            "created_at DESC "
            "LIMIT :lim OFFSET :off"
        )

    count_stmt = text("SELECT COUNT(*) FROM knowledge_bases WHERE soft_delete = false ")
    count_params = {}
    if status_filter:
        count_stmt = text(str(count_stmt) + "AND status = :status_filter")
        count_params["status_filter"] = status_filter

    count_result = await session.execute(count_stmt.bindparams(**count_params))
    total = count_result.scalar()

    result = await session.execute(stmt.bindparams(**params))
    rows = result.fetchall()

    items = []
    for row in rows:
        items.append(
            KnowledgeBaseResponse(
                id=row[0],
                org_id=row[1],
                title=row[2],
                source_type=row[3],
                source_url=row[4],
                file_path=row[5],
                file_storage_url=row[6],
                content_hash=row[7],
                chunk_count=row[8],
                status=row[9],
                error_message=row[10],
                metadata=row[11],
                created_at=row[12],
                updated_at=row[13],
            )
        )

    return DocumentListResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/documents/{document_id}", response_model=KnowledgeBaseResponse)
async def get_document(
    document_id: int,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id
    await _set_rls_context(session, org_id)

    kb_service = get_kb_service()
    doc = await kb_service.get_by_id(session, document_id)
    if not doc or doc.org_id != org_id:
        raise HTTPException(status_code=404, detail="Document not found")

    return KnowledgeBaseResponse(
        id=doc.id,
        org_id=doc.org_id,
        title=doc.title,
        source_type=doc.source_type,
        source_url=doc.source_url,
        file_path=doc.file_path,
        file_storage_url=doc.file_storage_url,
        content_hash=doc.content_hash,
        chunk_count=doc.chunk_count,
        status=doc.status,
        error_message=doc.error_message,
        metadata=doc.metadata,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id
    await _set_rls_context(session, org_id)

    kb_service = get_kb_service()
    doc = await kb_service.get_by_id(session, document_id)
    if not doc or doc.org_id != org_id:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status == "processing":
        raise HTTPException(
            status_code=409,
            detail="Cannot delete document while processing",
        )

    await session.execute(
        text(
            "UPDATE knowledge_chunks SET soft_delete = true "
            "WHERE knowledge_base_id = :kb_id AND org_id = :org_id"
        ),
        {"kb_id": document_id, "org_id": org_id},
    )
    deleted = await kb_service.mark_soft_deleted(session, document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    logger.info(
        "Deleted knowledge base %d for org %s",
        document_id,
        org_id,
        extra={
            "org_id": org_id,
            "source_type": doc.source_type,
            "transition": f"{doc.status}->deleted",
        },
    )

    return {"message": "Document deleted successfully"}


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id
    await _set_rls_context(session, org_id)

    embedding_service = get_embedding_service()
    query_embedding = await embedding_service.generate_embedding(request.query)

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
            "ORDER BY kc.embedding <=> :query_embedding::vector "
            "LIMIT :top_k"
        ),
        {
            "query_embedding": str(query_embedding),
            "org_id": org_id,
            "top_k": request.top_k,
        },
    )
    rows = result.fetchall()

    results = []
    for row in rows:
        results.append(
            {
                "chunk_id": row[0],
                "knowledge_base_id": row[1],
                "content": row[2],
                "metadata": row[3],
                "similarity": float(row[4]),
            }
        )

    return KnowledgeSearchResponse(
        results=results,
        total=len(results),
        query=request.query,
    )


@router.post("/documents/{document_id}/retry", response_model=RetryResponse)
async def retry_document(
    document_id: int,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    org_id = token.org_id
    await _set_rls_context(session, org_id)

    kb_service = get_kb_service()
    doc = await kb_service.get_by_id(session, document_id)
    if not doc or doc.org_id != org_id:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status != "failed":
        raise HTTPException(
            status_code=409,
            detail="Only failed documents can be retried",
        )

    if len(_background_tasks) >= MAX_BACKGROUND_TASKS:
        raise HTTPException(
            status_code=503,
            detail="Too many concurrent uploads, please try again later",
        )

    ingestion_service = get_ingestion_service()
    extracted_text = ""
    metadata = doc.metadata or {}
    file_path = None

    if doc.source_type == "pdf" and doc.file_path:
        file_path = doc.file_path
        if Path(file_path).exists():
            try:
                extracted_text, metadata = await ingestion_service.extract_pdf(
                    file_path
                )
            except IngestionError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        else:
            raise HTTPException(
                status_code=400,
                detail="Original file no longer available for retry",
            )
    elif doc.source_type == "url" and doc.source_url:
        try:
            extracted_text, metadata = await ingestion_service.extract_url(
                doc.source_url
            )
        except IngestionError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    elif doc.source_type == "text":
        raise HTTPException(
            status_code=400,
            detail="Text documents cannot be retried; please re-upload",
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="No source available for retry",
        )

    await session.execute(
        text(
            "UPDATE knowledge_bases "
            "SET status = 'processing', error_message = NULL, updated_at = NOW() "
            "WHERE id = :doc_id AND org_id = :org_id"
        ),
        {"doc_id": document_id, "org_id": org_id},
    )
    await session.commit()

    task = asyncio.create_task(
        _process_ingestion(
            document_id,
            extracted_text,
            metadata,
            org_id,
            doc.source_type,
            file_path if doc.source_type == "pdf" else None,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    logger.info(
        "Retrying knowledge base %d for org %s",
        document_id,
        org_id,
        extra={
            "org_id": org_id,
            "source_type": doc.source_type,
            "transition": "failed->processing",
        },
    )

    return RetryResponse(
        knowledge_base_id=document_id,
        status=KnowledgeStatus.processing,
        message="Document retry initiated",
    )
