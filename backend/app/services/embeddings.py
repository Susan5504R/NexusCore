import logging
from typing import Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings

logger = logging.getLogger("nexuscore.embeddings")

def get_embeddings() -> Any:
    """
    Returns the appropriate Embeddings instance based on config.
    Prioritizes OpenAI if configured, otherwise falls back to Google Gemini.
    """
    settings = get_settings()
    
    if settings.openai_api_key:
        return OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key,
            max_retries=settings.max_retries,
            timeout=60.0
        )

    if not settings.gemini_api_key:
        raise ValueError("Either OPENAI_API_KEY or GEMINI_API_KEY must be configured for embeddings")

    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.gemini_api_key,
        max_retries=5
    )
