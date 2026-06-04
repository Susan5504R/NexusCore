import logging

from langchain_openai import ChatOpenAI

from app.core.config import get_settings

logger = logging.getLogger("nexuscore.llm")

def _build_default_headers() -> dict[str, str]:
    settings = get_settings()
    headers = {"X-Title": settings.openrouter_title}
    if settings.openrouter_referer:
        headers["HTTP-Referer"] = settings.openrouter_referer
    return headers


def _create_openrouter_model() -> ChatOpenAI:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured")

    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
        model=settings.openrouter_chat_model,
        temperature=0.0,
        max_retries=settings.max_retries,
        default_headers=_build_default_headers(),
    )


def get_chat_model() -> ChatOpenAI:
    """
    Returns a configured OpenRouter chat model for inference.
    We use temperature=0 for deterministic SRE reasoning.
    """
    return _create_openrouter_model()


def get_security_model() -> ChatOpenAI:
    """
    Returns the LLM responsible for arbitration and guardrails.
    Uses the same deterministic model for simplicity.
    """
    return _create_openrouter_model()
