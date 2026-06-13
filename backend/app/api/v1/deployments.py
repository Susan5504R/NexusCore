import logging
from fastapi import APIRouter, Request, Depends

from app.core.schemas import PendingDeploymentsResponse, AckPayload
from app.security.auth import verify_api_key

logger = logging.getLogger("nexuscore.api.deployments")
router = APIRouter()

@router.get("/pending", response_model=PendingDeploymentsResponse, dependencies=[Depends(verify_api_key)])
async def get_pending(request: Request, auth_context=Depends(verify_api_key)):
    patch_store = getattr(request.app.state, "patch_store", None)
    if not patch_store:
        return {"patches": []}
        
    patches = await patch_store.poll(auth_context.namespace)
    return {"patches": patches}

@router.post("/ack", dependencies=[Depends(verify_api_key)])
async def acknowledge_patch(request: Request, payload: AckPayload, auth_context=Depends(verify_api_key)):
    patch_store = getattr(request.app.state, "patch_store", None)
    if not patch_store:
        return {"status": "error", "message": "PatchStore not initialized"}
        
    await patch_store.acknowledge(payload.patch_id, payload.status, payload.stderr)
    return {"status": "ok"}
