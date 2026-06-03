import logging
from app.core.schemas import AgentState
from app.services.sandbox import execute_in_sandbox

logger = logging.getLogger("nexuscore.nodes.sandbox")

async def sandbox_node(state: AgentState) -> dict:
    """
    Execution node.
    Runs the generated patch in the isolated Docker sandbox.
    """
    logger.info("--- SANDBOX VERIFICATION NODE ---")
    
    patch_code = state.get("proposed_patch", "")
    if not patch_code:
        logger.error("No patch code found to execute.")
        return {
            "execution_exit_code": 1,
            "execution_stderr": "No patch code provided by the LLM.",
            "retry_count": state.get("retry_count", 0) + 1
        }
        
    # Execute the code inside the ephemeral Docker container
    exit_code, stdout, stderr = await execute_in_sandbox(
        patch_code,
        project_path=state.get("project_path", ""),
        reproduction_command=state.get("reproduction_command", ""),
        target_file=state.get("current_target_file", "")
    )
    
    logger.info(f"Sandbox completed. Exit code: {exit_code}")
    if stderr:
        logger.warning(f"Sandbox Stderr: {stderr.strip()}")
        
    # Phase 5.4: Deploy the verified fix back to the actual project
    if exit_code == 0:
        project_path = state.get("project_path", "")
        target_file = state.get("current_target_file", "")
        if project_path and target_file:
            import os
            rel_target = os.path.relpath(target_file, project_path) if os.path.isabs(target_file) else target_file
            original_target = os.path.join(project_path, rel_target)
            
            # If the direct path doesn't exist, search the project tree
            if not os.path.exists(original_target):
                basename = os.path.basename(rel_target)
                for root, _dirs, files in os.walk(project_path):
                    if basename in files:
                        original_target = os.path.join(root, basename)
                        logger.info(f"Resolved deploy target to: {original_target}")
                        break
            
            try:
                os.makedirs(os.path.dirname(original_target), exist_ok=True)
                with open(original_target, 'w', encoding='utf-8') as f:
                    f.write(patch_code)
                logger.info(f"Fix verified! Patch successfully deployed to {original_target}")
            except Exception as e:
                logger.error(f"Failed to deploy verified patch: {e}")
                
    current_retries = state.get("retry_count", 0)
    
    return {
        "execution_exit_code": exit_code,
        "execution_stderr": stderr.strip(),
        "retry_count": current_retries + 1
    }
