import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import get_settings

logger = logging.getLogger("nexuscore.llm")

def get_chat_model() -> ChatGoogleGenerativeAI:
    """
    Returns a configured Gemini Chat model for inference.
    We use temperature=0 for deterministic SRE reasoning.
    """
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.gemini_chat_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.0,
        max_retries=5
    )

def get_security_model() -> ChatGoogleGenerativeAI:
    """
    Returns the LLM responsible for arbitration and guardrails.
    Uses the same deterministic model for simplicity.
    """
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.gemini_chat_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.0,
        max_retries=5
    )
