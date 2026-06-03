import logging
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.schemas import AgentState
from app.services.llm import get_chat_model

logger = logging.getLogger("nexuscore.nodes.modification")

class PatchProposal(BaseModel):
    reasoning: str = Field(description="Explanation of what caused the bug and how the patch fixes it.")
    python_code: str = Field(description="The complete, standalone, runnable Python script to fix the issue. It MUST run successfully in isolation without syntax errors.")

async def modification_node(state: AgentState) -> dict:
    """
    Code generation node.
    Reviews the context and previous errors to generate a patch.
    """
    logger.info("--- CODE MODIFICATION NODE ---")
    
    chat_model = get_chat_model()
    # include_raw=True preserves the AIMessage alongside the parsed Pydantic object
    # so we can read usage_metadata.total_tokens for real per-call token accounting.
    structured_llm = chat_model.with_structured_output(PatchProposal, include_raw=True)
    
    sys_content = "You are an autonomous Python SRE agent. Your goal is to write a standalone Python script that fixes the server error based on the context. Only provide valid, runnable Python code in the python_code field."
    
    user_messages = []
    for msg in state.get("messages", []):
        if msg["role"] == "system":
            sys_content += f"\n\n{msg['content']}"
        else:
            user_messages.append(HumanMessage(content=msg["content"]))
            
    langchain_messages = [SystemMessage(content=sys_content)] + user_messages
            
    # Inject previous execution failure if we are in a retry loop
    if state.get("execution_exit_code", -1) not in (-1, 0):
        error_msg = f"PREVIOUS ATTEMPT FAILED with stderr:\n{state.get('execution_stderr')}\n\nPlease analyze the error and provide a corrected Python script."
        langchain_messages.append(HumanMessage(content=error_msg))
        
    try:
        result = await structured_llm.ainvoke(langchain_messages)
        response: PatchProposal = result["parsed"]
        raw_message = result.get("raw")

        # Extract real token count from the AIMessage usage_metadata.
        # usage_metadata is None if the model config doesn't return it; default to 0.
        tokens_used = 0
        if raw_message is not None:
            meta = getattr(raw_message, "usage_metadata", None)
            if meta is not None:
                tokens_used = int(meta.get("total_tokens", 0))

        logger.info(f"Generated patch (tokens={tokens_used}). Reasoning: {response.reasoning}")

        assistant_message = {
            "role": "assistant",
            "content": f"Proposed Fix: {response.reasoning}\n\nCode:\n{response.python_code}"
        }

        return {
            "proposed_patch": response.python_code,
            "messages": [assistant_message],
            "token_consumption": tokens_used,
        }
    except Exception as e:
        logger.error(f"Modification generation failed: {e}", exc_info=True)
        return {
            "execution_exit_code": -1,
            "execution_stderr": f"LLM generation failed: {e}",
        }
