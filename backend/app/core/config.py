"""Central configuration for Nexus-Core.

A single typed Settings object loads and validates every environment variable at
startup. Required keys (Gemini, Pinecone) fail fast if missing; keys that later
phases depend on (Supabase, Groq) are optional here and validated only when the
feature that needs them is actually used.

Every service in the project reads its configuration through `get_settings()`,
which returns one cached instance for the whole process.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Required: inference + vector DB (Phase 1) ─────────────────────────
    gemini_api_key: str = Field(..., description="Google AI Studio API key.")
    pinecone_api_key: str = Field(..., description="Pinecone serverless API key.")

    # ── Optional until their phase comes online ───────────────────────────
    supabase_db_url: str | None = Field(
        default=None, description="Postgres connection URL for the ledger (Phase 0.4)."
    )
    groq_api_key: str | None = Field(
        default=None, description="Groq key for the security arbiter model (Phase 3.4)."
    )

    # ── Model selection ───────────────────────────────────────────────────
    gemini_chat_model: str = "gemini-3.5-flash"
    gemini_embedding_model: str = "models/gemini-embedding-001"
    embedding_dimension: int = 3072
    security_model: str = "llama-3.1-8b-instant"  # Groq, zero-temperature

    # ── Pinecone index (auto-created on startup if absent) ────────────────
    pinecone_index: str = "nexus-core"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_metric: str = "cosine"

    # ── Ingestion / RAG tuning ────────────────────────────────────────────
    chunk_size: int = 1200
    chunk_overlap: int = 150
    retrieval_top_k: int = 5

    # ── Docker sandbox (Phase 2) ──────────────────────────────────────────
    sandbox_image: str = "python:3.10-slim"
    sandbox_mem_limit: str = "128m"
    sandbox_nano_cpus: int = 500_000_000  # 0.5 CPU cores
    sandbox_network_mode: str = "none"
    sandbox_timeout_seconds: int = 30

    # ── Cost / latency guardrails (Operational Validation Checklist) ──────
    max_retries: int = 3

    # ── Anomaly detection (Phase 3) ───────────────────────────────────────
    anomaly_contamination: float = 0.05
    anomaly_window_size: int = 100

    # ── Server ────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("gemini_api_key", "pinecone_api_key")
    @classmethod
    def _reject_blank(cls, value: str, info) -> str:
        if not value or not value.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return value.strip()


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached Settings instance.

    Cached so the .env file is parsed once and every importer shares the same
    object. Tests can clear the cache via `get_settings.cache_clear()`.
    """
    return Settings()
