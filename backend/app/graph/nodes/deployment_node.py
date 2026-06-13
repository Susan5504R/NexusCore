import asyncio
import logging

from app.core.schemas import AgentState
from app.core.config import get_settings
from app.services.process_manager import RestartCircuitBreaker
from app.services.restart_strategies import get_restart_strategy

logger = logging.getLogger("nexuscore.graph.nodes.deployment")

async def deployment_node(state: AgentState) -> dict:
    """
    Post-heal deployment node.
    Restarts the target project after a verified patch has been written to disk.
    Only runs when sandbox_node has exit_code == 0.
    """
    logger.info("--- DEPLOYMENT NODE (POST-HEAL RESTART) ---")
    
    project_path = state.get("project_path", "")
    repro_cmd = state.get("reproduction_command", "")
    
    if not project_path or not repro_cmd:
        logger.warning("No project_path or reproduction_command — skipping restart.")
        return {
            "deployment_status": "skipped",
            "deployment_reason": "Missing project_path or command"
        }
    
    settings = get_settings()
    if not settings.enable_post_heal_restart:
        return {
            "deployment_status": "disabled",
            "deployment_reason": "Post-heal restart is disabled in config"
        }
        
    # --- Circuit Breaker & Dispatch ---
    circuit_breaker = RestartCircuitBreaker.get_instance()
    if not circuit_breaker.can_restart(project_path):
        logger.critical(f"🔴 Circuit breaker OPEN for {project_path}. Too many restart failures.")
        return {
            "deployment_status": "circuit_breaker_open",
            "deployment_reason": "Too many restart failures in time window"
        }
    
    strategy = get_restart_strategy(settings)
    try:
        circuit_breaker.record_attempt(project_path)
        logger.info(f"Triggering restart for {project_path} via {strategy.__class__.__name__}...")
        
        result = await strategy.restart(project_path, command=repro_cmd)
        
        if result.get("status") == "pending_daemon":
            return {
                "deployment_status": "pending_daemon",
                "deployment_reason": result.get("reason", "Patch queued for daemon pickup")
            }
        
        # Wait for the process to hopefully crash if it's still broken
        await asyncio.sleep(settings.restart_health_check_delay)
        health = await strategy.health_check(project_path)
        
        if health["alive"]:
            circuit_breaker.record_success(project_path)
            logger.info(f"✅ Project restarted and healthy. PID={health.get('pid')}")
            return {
                "deployment_status": "success",
                "deployment_pid": health.get("pid"),
                "deployment_reason": "Restart successful and passed health check"
            }
        else:
            logger.error(f"❌ Project restarted but failed health check.")
            return {
                "deployment_status": "unhealthy",
                "deployment_stderr": health.get("last_stderr", ""),
                "deployment_reason": "Process died immediately after restart"
            }
    except Exception as e:
        logger.error(f"Restart failed: {e}", exc_info=True)
        return {
            "deployment_status": "error",
            "deployment_reason": str(e)
        }
