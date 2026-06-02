import uuid
import time
import logging
from fastapi import APIRouter, Request, HTTPException

from app.core.schemas import GraphRunRequest, GraphRunResponse, OperationalLogEntry, new_agent_state
from app.graph.orchestrator import create_sre_orchestrator

logger = logging.getLogger("nexuscore.api.graph")
router = APIRouter()

# Instantiate the orchestrator once (it acts as a stateless workflow template)
sre_orchestrator = create_sre_orchestrator()

@router.post("/run", response_model=GraphRunResponse)
async def run_graph(request: Request, payload: GraphRunRequest):
    """
    Triggers a full execution of the autonomous SRE repair LangGraph.
    """
    start_time = time.perf_counter()
    run_id = str(uuid.uuid4())
    
    # Initialize a fresh LangGraph state memory using the request payload
    initial_state = new_agent_state(
        current_target_file=payload.target_file,
        discovered_logs=payload.logs
    )
    
    logger.info(f"Starting Graph Run {run_id} for target file: {payload.target_file}")
    
    try:
        # Execute the full cyclic graph.
        # This will spin through evaluation -> context -> modification -> sandbox -> routing
        # until the routing conditional hits the END node.
        final_state = await sre_orchestrator.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"Graph execution fatally failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
        
    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    
    # Extract the results from the final AgentState
    exit_code = final_state.get("execution_exit_code", -1)
    retry_count = final_state.get("retry_count", 0)
    clearance = final_state.get("security_clearance", False)
    patch = final_state.get("proposed_patch", "")
    
    response_data = GraphRunResponse(
        run_id=run_id,
        final_exit_code=exit_code,
        retry_count=retry_count,
        security_clearance=clearance,
        proposed_patch=patch
    )
    
    # Record the autonomous action in the operational ledger
    ledger = getattr(request.app.state, "ledger", None)
    if ledger:
        # Determine strict final status
        status = "success" if exit_code == 0 else "failed"
        if not clearance:
            status = "blocked_security"
            
        entry = OperationalLogEntry(
            event_source="api/v1/graph/run",
            agent_action="autonomous_repair",
            execution_payload=f"Target: {payload.target_file} | Retries: {retry_count}",
            execution_status=status,
            compute_latency_ms=elapsed_ms
        )
        await ledger.log_event(entry)
        
    return response_data
