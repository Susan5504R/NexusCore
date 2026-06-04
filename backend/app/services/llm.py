import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

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

def _create_anthropic_model() -> ChatAnthropic:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured")
        
    return ChatAnthropic(
        model_name=settings.anthropic_chat_model,
        anthropic_api_key=settings.anthropic_api_key,
        temperature=0.0,
        max_retries=settings.max_retries,
    )

def get_chat_model() -> Any:
    """
    Returns a configured chat model for inference.
    Prefers Anthropic if configured, falls back to Gemini.
    We use temperature=0 for deterministic SRE reasoning.
    """
    settings = get_settings()
    if settings.anthropic_api_key:
        logger.info("Using Anthropic for chat inference")
        return _create_anthropic_model()
    
    logger.info("Using Gemini for chat inference")
    return _create_gemini_model()

def get_security_model() -> Any:
    """
    Returns the LLM responsible for arbitration and guardrails.
    Prefers Anthropic if configured, falls back to Gemini.
    """
    settings = get_settings()
    if settings.anthropic_api_key:
        logger.info("Using Anthropic for security arbitration")
        return _create_anthropic_model()
        
    logger.info("Using Gemini for security arbitration")
    return _create_gemini_model()
