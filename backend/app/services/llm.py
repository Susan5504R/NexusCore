import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings

logger = logging.getLogger("nexuscore.llm")


def _create_gemini_model() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured")

    return ChatGoogleGenerativeAI(
        model=settings.gemini_chat_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.0,
        max_retries=settings.max_retries,
    )


def get_chat_model() -> ChatGoogleGenerativeAI:
    """
    Returns a configured Gemini chat model for inference.
    We use temperature=0 for deterministic SRE reasoning.
    """
    return _create_gemini_model()


def get_security_model() -> ChatGoogleGenerativeAI:
    """
    Returns the LLM responsible for arbitration and guardrails.
    Uses the same deterministic model for simplicity.
    """
    return _create_gemini_model()
