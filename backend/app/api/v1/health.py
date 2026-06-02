"""Health endpoint — reports per-dependency readiness.

Checks are intentionally cheap so the dashboard can poll this frequently:
* Gemini   — is an API key configured?
* Pinecone — was the client built, and can we list indexes?
* Docker   — wired in Phase 2.1 (reports 'not_configured' until then).
* Ledger   — wired in Phase 0.4 (reports 'not_configured' until then).
"""

from fastapi import APIRouter, Request

from app.core.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    state = request.app.state
    settings = state.settings
    deps: dict[str, str] = {}

    deps["gemini"] = "ok" if settings.gemini_api_key else "not_configured"

    pinecone_client = getattr(state, "pinecone", None)
    if pinecone_client is None:
        deps["pinecone"] = "error"
    else:
        try:
            pinecone_client.list_indexes()
            deps["pinecone"] = "ok"
        except Exception:  # noqa: BLE001 - degraded, not fatal
            deps["pinecone"] = "error"

    deps["docker"] = "ok" if getattr(state, "docker_client", None) else "not_configured"

    ledger = getattr(state, "ledger", None)
    if ledger is None:
        deps["ledger"] = "not_configured"
    else:
        deps["ledger"] = "ok" if await ledger.ping() else "error"

    overall = "ok" if all(v == "ok" for v in (deps["gemini"], deps["pinecone"])) else "degraded"
    return HealthResponse(status=overall, dependencies=deps)
