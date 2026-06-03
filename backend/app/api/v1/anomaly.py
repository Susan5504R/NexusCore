import logging
from fastapi import APIRouter, Request, BackgroundTasks, Depends

from app.core.schemas import AnomalyPayload
from app.services.graph_runner import execute_repair
from app.security.auth import verify_webhook_signature

logger = logging.getLogger("nexuscore.api.anomaly")
router = APIRouter()

@router.post("/trigger", dependencies=[Depends(verify_webhook_signature)])
async def trigger_anomaly(
    request: Request,
    payload: AnomalyPayload,
    background_tasks: BackgroundTasks
):
    """
    Webhook endpoint for external alerting tools (Datadog, PagerDuty, Sentry).
    Immediately acknowledges the alert with HTTP 200 to prevent webhook timeouts,
    and dispatches the autonomous LangGraph repair cycle into the background.
    """
    logger.warning(f"🚨 Received ANOMALY ALERT [{payload.alert_id}] for service '{payload.service_name}'")
    
    # Dispatch the repair process to the background
    background_tasks.add_task(
        execute_repair, 
        app=request.app, 
        target_file=payload.target_file, 
        logs=payload.logs, 
        run_id=payload.alert_id,
        event_source="api/v1/anomaly/trigger"
    )
    
    return {
        "status": "accepted",
        "message": "Anomaly received. Autonomous SRE repair dispatched in background.",
        "alert_id": payload.alert_id
    }
