import time
import logging
from typing import List

from app.core.schemas import AgentState, new_agent_state, OperationalLogEntry
from app.graph.orchestrator import create_sre_orchestrator

logger = logging.getLogger("nexuscore.services.graph_runner")

# Instantiate the orchestrator once (it acts as a stateless workflow template)
sre_orchestrator = create_sre_orchestrator()

async def record_ledger_entry(app, target_file: str, final_state: AgentState, elapsed_ms: int, run_id: str, event_source: str):
    """Helper to write a finished run to the ledger."""
    ledger = getattr(app.state, "ledger", None)
    if not ledger:
        return

    exit_code = final_state.get("execution_exit_code", -1)
    clearance = final_state.get("security_clearance", False)
    retry_count = final_state.get("retry_count", 0)
    
    status = "success" if exit_code == 0 else "failed"
    if not clearance:
        status = "blocked_security"
        
    entry = OperationalLogEntry(
        event_source=event_source,
        agent_action="autonomous_repair",
        execution_payload=f"Target: {target_file} | Retries: {retry_count}",
        execution_status=status,
        compute_latency_ms=elapsed_ms
    )
    try:
        await ledger.log_event(entry)
    except Exception as ledger_err:
        logger.error(f"Failed to record to ledger: {ledger_err}")


async def execute_repair(app, target_file: str, logs: List[str], run_id: str, event_source: str = "api/v1/graph/run") -> AgentState:
    """
    Executes the SRE graph entirely and writes to the ledger.
    Provides a unified invocation path for both REST endpoints and background triggers.
    """
    start_time = time.perf_counter()
    initial_state = new_agent_state(
        current_target_file=target_file,
        discovered_logs=logs
    )
    
    logger.info(f"Starting Graph Run {run_id} for target file: {target_file}")
    
    try:
        final_state = await sre_orchestrator.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"Graph execution fatally failed: {e}", exc_info=True)
        raise
        
    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    await record_ledger_entry(app, target_file, final_state, elapsed_ms, run_id, event_source)
            
    return final_state
