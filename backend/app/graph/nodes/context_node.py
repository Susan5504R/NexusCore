import logging
from app.core.schemas import AgentState
from app.services.vectorstore import get_vectorstore_service

logger = logging.getLogger("nexuscore.nodes.context")

async def context_node(state: AgentState) -> dict:
    """
    Retrieval node.
    Uses the discovered logs and target to query the vectorstore for context.
    """
    logger.info("--- CONTEXT RETRIEVAL NODE ---")
    
    logs = "\n".join(state.get("discovered_logs", []))
    query = f"Error in {state.get('current_target_file')}: {logs}"
    
    try:
        vectorstore = get_vectorstore_service()
        # Fetch top relevant chunks
        docs = await vectorstore.asearch(query, top_k=3)
        
        context_blocks = []
        for doc in docs:
            path = doc.metadata.get("path", "Unknown")
            context_blocks.append(f"--- File: {path} ---\n{doc.page_content}")
            
        assembled_context = "\n\n".join(context_blocks)
        
        context_message = {
            "role": "system",
            "content": f"Retrieved Context from Codebase:\n{assembled_context}"
        }
        
        return {"messages": [context_message]}
    except Exception as e:
        logger.error(f"Context retrieval failed: {e}")
        return {"messages": [{"role": "system", "content": f"Failed to retrieve context: {e}"}]}
