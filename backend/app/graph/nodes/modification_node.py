import logging
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.schemas import AgentState
from app.services.llm import get_chat_model

logger = logging.getLogger("nexuscore.nodes.modification")

class PatchProposal(BaseModel):
    reasoning: str = Field(description="Explanation of what caused the bug and how the patch fixes it.")
    target_file: str = Field(description="The exact relative path of the file you are modifying. If the user provided AUTO_DETECT or a blank target, you MUST deduce the correct filename from the retrieved codebase context.")
    code: str = Field(description="The complete, updated content of the target file. It MUST be the full file content, not just a diff or snippet.")

async def modification_node(state: AgentState) -> dict:
    """
    Code generation node.
    Reviews the context and previous errors to generate a full-file patch.
    """
    logger.info("--- CODE MODIFICATION NODE ---")
    
    chat_model = get_chat_model()
    structured_llm = chat_model.with_structured_output(PatchProposal, include_raw=True)
    
    sys_content = "You are an autonomous polyglot SRE agent. Your goal is to review the crash logs and the provided codebase context, and rewrite the COMPLETE target file with a fix. Determine the programming language from the file extension. Return the FULL updated file content in the 'code' field and the exact relative path in 'target_file'. DO NOT return a standalone snippet or diffs, return the entire modified file so it can be overwritten safely."
    
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
        
    from app.core.config import get_settings
    if get_settings().use_mock_llm:
        logger.info("Using mock patch generation (quota-free mode)")
        mock_patch = """import sys
import time
import math

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
        raise SystemExit(1)

if __name__ == "__main__":
    main()"""
        assistant_message = {
            "role": "assistant",
            "content": "Proposed Fix (MOCKED): Imported math and updated the square root logic inside process_metrics."
        }
        return {
            "proposed_patch": mock_patch,
            "current_target_file": "buggy_server.py",
            "messages": [assistant_message],
            "token_consumption": 0,
        }

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
            "content": f"Proposed Fix for {response.target_file}: {response.reasoning}\n\nCode:\n{response.code}"
        }

        return {
            "proposed_patch": response.code,
            "current_target_file": response.target_file,
            "messages": [assistant_message],
            "token_consumption": tokens_used,
        }
    except Exception as e:
        logger.error(f"Modification generation failed: {e}", exc_info=True)
        return {
            "execution_exit_code": -1,
            "execution_stderr": f"LLM generation failed: {e}",
        }
