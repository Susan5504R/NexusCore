"""Application lifespan: build shared clients once, tear them down cleanly.

Long-lived resources (the Pinecone client, and in later phases the Docker client
and ledger pool) are created at startup and stashed on ``app.state`` so every
request handler can reach them via ``request.app.state`` without re-connecting.

The startup is deliberately tolerant: if an optional dependency can't be reached,
the app still boots and the health endpoint reports the degraded status. Required
secrets are already enforced fail-fast by Settings.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pinecone import Pinecone

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.ledger import create_ledger

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings

    # ── Pinecone client ───────────────────────────────────────────────────
    # Constructed here; index auto-create + queries live in the vectorstore
    # service (Phase 1.2). We only verify the client can be built.
    app.state.pinecone = None
    try:
        app.state.pinecone = Pinecone(api_key=settings.pinecone_api_key)
        logger.info("pinecone client initialized")
    except Exception as exc:  # noqa: BLE001 - boot must survive a bad/placeholder key
        logger.error("pinecone client init failed", extra={"error": str(exc)})

    # ── Operational ledger (Supabase / Postgres) ───────────────────────────
    app.state.ledger = await create_ledger(settings.supabase_db_url)

    # ── Filled by later phases ──────────────────────────────────────────────
    # Phase 2.1 sets app.state.docker_client.
    app.state.docker_client = None

    logger.info("nexus-core startup complete")
    yield

    # ── Shutdown ────────────────────────────────────────────────────────────
    if getattr(app.state, "ledger", None) is not None:
        await app.state.ledger.close()
    if getattr(app.state, "docker_client", None) is not None:
        try:
            app.state.docker_client.close()
        except Exception as exc:  # noqa: BLE001
            logger.error("docker client close failed", extra={"error": str(exc)})
    logger.info("nexus-core shutdown complete")
