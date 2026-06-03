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
    
    from app.core.config import get_settings
    if get_settings().use_mock_llm:
        logger.info("Using mock context retrieval (quota-free mode)")
        mock_context = """--- File: buggy_server.py ---
import sys
import time

def process_metrics():
    metrics = [10, 20, -5, 40]
    for m in metrics:
        if m < 0:
            val = math.sqrt(abs(m))
            print(f"Processed absolute metric: {val}")
        else:
            print(f"Processed metric: {m}")
        time.sleep(0.5)

def main():
    print("Starting NexusCore Demo Server...")
    try:
        process_metrics()
        print("Server running successfully!")
    except Exception as e:
        print(f"FATAL CRASH: {type(e).__name__}: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()"""
        return {"messages": [{"role": "system", "content": f"Retrieved Context from Codebase:\n{mock_context}"}]}

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
