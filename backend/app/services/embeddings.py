import logging
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import get_settings

logger = logging.getLogger("nexuscore.embeddings")

def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """
    Returns the Google Generative AI Embeddings instance based on config.
    Defaults to models/gemini-embedding-001 (3072 dims), matching the Pinecone
    index dimension in settings.
    """
    settings = get_settings()
    
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.gemini_api_key,
        max_retries=5
    )
