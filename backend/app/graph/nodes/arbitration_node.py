import logging
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from app.core.schemas import AgentState
from app.services.llm import get_security_model
from app.security.blocklist import check_blocklist

logger = logging.getLogger("nexuscore.nodes.arbitration")

class SecurityDecision(BaseModel):
    is_safe: bool = Field(description="True if the code is safe. False if it contains destructive or unauthorized operations.")
    reason: str = Field(description="Brief explanation of the security decision.")

async def arbitration_node(state: AgentState) -> dict:
    """
    Security gate. Analyzes the proposed patch for destructive commands before allowing sandboxing.
    """
    logger.info("--- SECURITY ARBITRATION NODE ---")
    
    patch = state.get("proposed_patch", "")
    if not patch:
        logger.warning("No patch found to arbitrate.")
        return {"security_clearance": False}
        
    # 1. Fast, deterministic static analysis (Regex Blocklist)
    is_safe_static, static_reason = check_blocklist(patch)
    if not is_safe_static:
        logger.warning(f"❌ Blocklist triggered: {static_reason}")
        return {"security_clearance": False}
        
    # 2. Heuristic dynamic analysis (LLM Arbitration)
    security_model = get_security_model().with_structured_output(SecurityDecision)
    
    prompt = f"""
    You are a strict DevSecOps AI. Analyze the following Python script.
    If the script contains destructive operations (e.g., os.system('rm -rf'), malicious subprocess calls, unauthorized network exfiltration), mark it as UNSAFE (is_safe=False).
    If it is a standard application logic fix, mark it as SAFE (is_safe=True).
    
    Code to evaluate:
    ```python
    {patch}
    ```
    """
    
    try:
        decision = await security_model.ainvoke([SystemMessage(content=prompt)])
        logger.info(f"Security decision: {'✅ SAFE' if decision.is_safe else '❌ UNSAFE'} ({decision.reason})")
        return {"security_clearance": decision.is_safe}
    except Exception as e:
        logger.error(f"Security arbitration failed (failing closed): {e}")
        return {"security_clearance": False}
