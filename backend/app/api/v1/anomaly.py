import logging
from fastapi import APIRouter, Request, BackgroundTasks

from app.core.schemas import AnomalyPayload, GraphRunRequest
from app.api.v1.graph import run_graph

logger = logging.getLogger("nexuscore.api.anomaly")
router = APIRouter()

@router.post("/trigger")
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
    
    # Map the anomaly payload to our internal Graph run schema
    graph_request = GraphRunRequest(
        target_file=payload.target_file,
        logs=payload.logs
    )
    
    # Dispatch the run_graph endpoint logic into the background event loop
    background_tasks.add_task(run_graph, request, graph_request)
    
    return {
        "status": "accepted",
        "message": "Anomaly received. Autonomous SRE repair dispatched in background.",
        "alert_id": payload.alert_id
    }
