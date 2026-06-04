import logging
from typing import List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Request, HTTPException, Depends

from app.security.auth import verify_api_key, AuthContext
from app.core.limiter import limiter
from app.services.api_keys import ApiKeyService

logger = logging.getLogger("nexuscore.api.keys")
router = APIRouter(prefix="/keys")

class GenerateKeyRequest(BaseModel):
    namespace: str
    label: str = ""

@router.post("", response_model=Dict[str, str])
@limiter.limit("10/minute")
async def generate_api_key(request: Request, payload: GenerateKeyRequest, auth: AuthContext = Depends(verify_api_key)):
    """
    Generates a new SaaS API key for the given namespace.
    Only accessible via the master dev key.
    """
    if auth.namespace is not None:
        raise HTTPException(status_code=403, detail="Admin access required")

    ledger = getattr(request.app.state, "ledger", None)
    if not ledger:
        raise HTTPException(status_code=503, detail="Ledger unavailable")
        
    try:
        svc = ApiKeyService(ledger)
        raw_key = await svc.generate_key(namespace=payload.namespace, label=payload.label)
        return {"raw_key": raw_key, "message": "Store this key safely. It will not be shown again."}
    except Exception as e:
        logger.error(f"Failed to generate API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate API key")

@router.get("", response_model=List[Dict[str, Any]])
@limiter.limit("30/minute")
async def list_api_keys(request: Request, auth: AuthContext = Depends(verify_api_key)):
    """
    Lists metadata for all SaaS API keys (never the raw keys).
    """
    if auth.namespace is not None:
        raise HTTPException(status_code=403, detail="Admin access required")

    ledger = getattr(request.app.state, "ledger", None)
    if not ledger:
        raise HTTPException(status_code=503, detail="Ledger unavailable")
        
    try:
        svc = ApiKeyService(ledger)
        keys = await svc.list_keys()
        return keys
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(status_code=500, detail="Failed to list API keys")
