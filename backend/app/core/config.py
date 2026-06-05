"""Central configuration for Nexus-Core.

A single typed Settings object loads and validates every environment variable at
startup. OpenRouter drives chat inference, Gemini stays optional for embeddings,
and keys that later phases depend on (Supabase) are validated only when the
feature that needs them is actually used.

Every service in the project reads its configuration through `get_settings()`,
which returns one cached instance for the whole process.
"""

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Required: inference + vector DB (Phase 1) ─────────────────────────
    openrouter_api_key: str | None = Field(
        default=None, description="OpenRouter API key for chat inference."
    )
    pinecone_api_key: str | None = Field(
        default=None, description="Pinecone serverless API key."
    )

    # ── Deployment Mode Foundation (Phase 0) ──────────────────────────────
    deployment_mode: str = "cloud"
    chroma_host: str | None = None
    chroma_port: int = 8000
    chroma_collection_prefix: str = "nexus_"

    @property
    def is_cloud(self) -> bool:
        return self.deployment_mode == "cloud"

    @property
    def is_local(self) -> bool:
        return self.deployment_mode == "local"

    # ── Optional until their phase comes online ───────────────────────────
    gemini_api_key: str | None = Field(
        default=None, description="Google AI Studio API key for Gemini embeddings."
    )
    anthropic_api_key: str | None = Field(
        default=None, description="Anthropic API key for Claude inference."
    )
    openai_api_key: str | None = Field(
        default=None, description="OpenAI API key for high-speed embeddings."
    )
    supabase_db_url: str | None = Field(
        default=None, description="Postgres connection URL for the ledger (Phase 0.4)."
    )

    # ── Model selection ───────────────────────────────────────────────────
    # The security arbiter (Phase 3.4) runs on the same OpenRouter model at
    # 0 for deterministic, zero-creativity safety assessment — see services/llm.py.
    openrouter_chat_model: str = "mistralai/mistral-7b-instruct:free"
    openrouter_referer: str | None = None
    openrouter_title: str = "Nexus-Core SRE"
    gemini_chat_model: str = "gemini-2.5-flash"
    anthropic_chat_model: str = "claude-3-5-sonnet-20241022"
    gemini_embedding_model: str = "models/gemini-embedding-001"
    openai_embedding_model: str = "text-embedding-3-small"
    use_local_embeddings: bool = False
    
    @property
    def embedding_dimension(self) -> int:
        if self.use_local_embeddings:
            return 384
        if self.openai_api_key:
            return 1536
        return 3072

    # ── Pinecone index (auto-created on startup if absent) ────────────────
    @property
    def pinecone_index(self) -> str:
        if self.use_local_embeddings:
            return "nexus-core-local"
        return "nexus-core"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_metric: str = "cosine"

    # ── Ingestion / RAG tuning ────────────────────────────────────────────
    chunk_size: int = 1200
    chunk_overlap: int = 150
    retrieval_top_k: int = 5

    # ── Sandbox (Phase 2) ─────────────────────────────────────────────────
    # "subprocess" = runs patches locally (fast, reliable on Windows dev)
    # "docker"     = runs patches in an isolated Docker container (production)
    sandbox_mode: str = "subprocess"
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
    # Off by default: when enabled, the background loop samples metrics and can
    # autonomously fire real graph runs (LLM + Docker). Opt in deliberately.
    enable_telemetry_loop: bool = False

    # ── Server ────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        # Cloud deployment (Vercel)
        "https://nexuscore.vercel.app",
        "https://nexuscore-frontend.vercel.app",
        "https://nexus-core.vercel.app",
    ]
    
    # ── Mock/Demo Mode (allows testing without API keys / quotas) ────────
    use_mock_llm: bool = False

    # ── Security & Auth (Phase 5.5) ───────────────────────────────────────
    nexus_api_key: str = "nexus-dev-key"
    nexus_webhook_secret: str = "nexus-dev-secret"

    @field_validator("openrouter_api_key", "gemini_api_key", "anthropic_api_key", mode="before")
    @classmethod
    def _normalize_optional_keys(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("deployment_mode", mode="before")
    @classmethod
    def _normalize_mode(cls, value: str) -> str:
        v = value.strip().lower()
        if v not in ("cloud", "local"):
            raise ValueError("deployment_mode must be 'cloud' or 'local'")
        return v

    @field_validator("pinecone_api_key")
    @classmethod
    def _reject_blank(cls, value: str | None, info) -> str | None:
        if value is not None and not value.strip():
            raise ValueError(f"{info.field_name} must not be empty if provided")
        return value.strip() if value else None

    @model_validator(mode="after")
    def _validate_deployment_mode_requirements(self) -> "Settings":
        if self.deployment_mode == "cloud":
            if not self.pinecone_api_key:
                raise ValueError("pinecone_api_key is required when deployment_mode is 'cloud'")
        elif self.deployment_mode == "local":
            if not self.chroma_host:
                raise ValueError("chroma_host is required when deployment_mode is 'local'")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached Settings instance.

    Cached so the .env file is parsed once and every importer shares the same
    object. Tests can clear the cache via `get_settings.cache_clear()`.
    """
    return Settings()
