import time
import logging
from fastapi import APIRouter, Request, HTTPException, Depends

from app.core.schemas import IngestRequest, IngestResponse, OperationalLogEntry
from app.services.ingestion import ingest_directory
from app.services.vectorstore import get_vectorstore_service
from app.security.auth import verify_api_key
from app.core.limiter import limiter

logger = logging.getLogger("nexuscore.api.ingest")
router = APIRouter()

@router.post("/ingest", response_model=IngestResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("2/minute")
async def ingest_codebase(request: Request, payload: IngestRequest):
    """
    Ingests a local directory, splitting the code into language-aware chunks
    and upserting them into the Pinecone vectorstore.
    """
    start_time = time.perf_counter()
    
    # 1. Read and chunk the directory
    try:
        chunks = await ingest_directory(payload.directory_path)
    except ValueError as ve:
        # Directory not found
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("Ingestion chunking failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest directory: {e}")
        
    if not chunks:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return IngestResponse(files_processed=0, chunks_indexed=0, elapsed_ms=elapsed_ms)

    # 2. Upsert chunks into VectorStore
    try:
        vectorstore_service = get_vectorstore_service()
        # Pass namespace if provided
        await vectorstore_service.aupsert_documents(chunks, namespace=payload.namespace)
    except Exception as e:
        logger.error("Vectorstore upsert failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upsert chunks: {e}")
        
    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    unique_files = len(set(chunk.metadata.get("path") for chunk in chunks if chunk.metadata.get("path")))
    
    response_data = IngestResponse(
        files_processed=unique_files,
        chunks_indexed=len(chunks),
        elapsed_ms=elapsed_ms
    )
    
    # 3. Log to operational ledger
    ledger = getattr(request.app.state, "ledger", None)
    if ledger:
        entry = OperationalLogEntry(
            event_source="api/v1/ingest",
            agent_action="ingest_codebase",
            execution_payload=f"directory: {payload.directory_path} | namespace: {payload.namespace}",
            execution_status="success",
            compute_latency_ms=elapsed_ms
        )
        # Log asynchronously (awaited because it uses asyncpg and is very fast)
        await ledger.log_event(entry)
        
    return response_data

@router.get("/ingest/files", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def list_ingested_files(request: Request, namespace: str = None):
    """
    Returns a list of unique file paths currently ingested in the given namespace.
    """
    try:
        vectorstore_service = get_vectorstore_service()
        files = await vectorstore_service.aget_unique_files(namespace=namespace)
        return {"files": files}
    except Exception as e:
        logger.error("Failed to list ingested files", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
