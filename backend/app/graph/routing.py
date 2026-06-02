import logging
from typing import Literal
from app.core.schemas import AgentState

logger = logging.getLogger("nexuscore.routing")

def route_security(state: AgentState) -> Literal["sandbox_node", "__end__"]:
    """
    Determines if the patch passed security arbitration and can be executed.
    """
    if state.get("security_clearance", False):
        return "sandbox_node"
    return "__end__"

def route_execution(state: AgentState) -> Literal["modification_node", "__end__"]:
    """
    Determines the next edge in the LangGraph based on execution status.
    Returns the string name of the next node to execute.
    """
    logger.info("--- EVALUATING ROUTING LOGIC ---")
    
    # 1. Security Check
    if not state.get("security_clearance", False):
        logger.warning("Execution blocked: No security clearance.")
        return "__end__"
        
    # 2. Success Check
    exit_code = state.get("execution_exit_code", -1)
    if exit_code == 0:
        logger.info("✅ Execution successful! Patch works. Exiting graph.")
        return "__end__"
        
    # 3. Retry Limit Check
    retries = state.get("retry_count", 0)
    if retries >= 3:
        logger.error("❌ Maximum retries (3) reached. Exiting graph to prevent infinite loops.")
        return "__end__"
        
    # 4. Loop back for another try
    logger.info(f"⚠️ Execution failed (Exit Code: {exit_code}). Routing back to modification_node for retry {retries}/3.")
    return "modification_node"
