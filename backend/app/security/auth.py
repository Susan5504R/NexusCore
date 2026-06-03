import hmac
import hashlib
import logging
from fastapi import Security, HTTPException, Request, Header
from fastapi.security import APIKeyHeader
from app.core.config import get_settings

logger = logging.getLogger("nexuscore.security.auth")

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency to verify the Authorization header or x-api-key matches the configured nexus_api_key.
    Extracts the key if passed as 'Bearer <token>' or raw.
    """
    settings = get_settings()
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing Authentication Token")
        
    # Handle optional Bearer prefix
    if api_key.lower().startswith("bearer "):
        api_key = api_key[7:].strip()
        
    if not hmac.compare_digest(api_key, settings.nexus_api_key):
        logger.warning("Failed API key authentication attempt")
        raise HTTPException(status_code=401, detail="Invalid Authentication Token")
        
    return api_key

async def verify_webhook_signature(request: Request, x_nexus_signature: str = Header(None)):
    """
    Dependency to verify HMAC SHA-256 signature for incoming webhooks.
    """
    settings = get_settings()
    
    if not x_nexus_signature:
        raise HTTPException(status_code=401, detail="Missing X-Nexus-Signature Header")
        
    body = await request.body()
    
    expected_signature = hmac.new(
        key=settings.nexus_webhook_secret.encode('utf-8'),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(x_nexus_signature, expected_signature):
        logger.warning("Failed webhook signature verification")
        raise HTTPException(status_code=401, detail="Invalid Webhook Signature")
        
    return True
