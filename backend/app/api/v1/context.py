import json
import logging
from fastapi import APIRouter, Request, HTTPException
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.schemas import ContextQueryRequest, OperationalLogEntry
from app.services.vectorstore import get_vectorstore_service
from app.services.llm import get_chat_model

logger = logging.getLogger("nexuscore.api.context")
router = APIRouter()

SYSTEM_PROMPT = """You are Nexus-Core, an autonomous SRE assistant. 
Use the provided codebase context to answer the user's prompt accurately. 
If the context doesn't contain the answer, state that you cannot find the answer in the codebase.
"""

@router.post("/context/query")
async def context_query(request: Request, payload: ContextQueryRequest):
    """
    RAG inference loop:
    1. Embed prompt and retrieve relevant codebase chunks.
    2. Assemble context window with explicit file paths.
    3. Stream response via SSE.
    """
    vectorstore = get_vectorstore_service()
    
    # 1. Retrieve chunks
    try:
        docs = await vectorstore.asearch(
            payload.prompt, 
            top_k=payload.top_k, 
            namespace=payload.namespace
        )
    except Exception as e:
        logger.error(f"Vector search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve context")

    # 2. Assemble context
    context_blocks = []
    for doc in docs:
        path = doc.metadata.get("path", "Unknown")
        context_blocks.append(f"--- File: {path} ---\n{doc.page_content}")
    
    assembled_context = "\n\n".join(context_blocks)
    
    user_message = f"Context:\n{assembled_context}\n\nPrompt:\n{payload.prompt}"

    # 3. Stream inference
    chat_model = get_chat_model()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message)
    ]
    
    async def event_generator():
        try:
            # astream yields AIMessageChunks
            async for chunk in chat_model.astream(messages):
                if chunk.content:
                    yield {
                        "event": "message",
                        "data": json.dumps({"text": chunk.content})
                    }
            
            # Log to operational ledger at the end of the stream
            ledger = getattr(request.app.state, "ledger", None)
            if ledger:
                entry = OperationalLogEntry(
                    event_source="api/v1/context/query",
                    agent_action="rag_inference",
                    execution_payload=f"prompt: {payload.prompt}",
                    execution_status="success"
                )
                await ledger.log_event(entry)
                
            # Signal the client that the stream is finished
            yield {"event": "done", "data": "[DONE]"}
            
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
