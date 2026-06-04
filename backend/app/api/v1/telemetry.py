import logging
from fastapi import APIRouter, Request, BackgroundTasks, Depends
from app.core.schemas import TelemetryIngestPayload
from app.core.schemas import GraphRunRequest
from app.services.graph_runner import execute_repair
from app.security.auth import verify_api_key

logger = logging.getLogger("nexuscore.api.telemetry")
router = APIRouter()

@router.post("/ingest", dependencies=[Depends(verify_api_key)])
async def ingest_telemetry(
    request: Request,
    payload: TelemetryIngestPayload,
    background_tasks: BackgroundTasks,
    auth_context = Depends(verify_api_key)
):
    """
    Cloud‑managed telemetry webhook. Receives metric payloads from the client daemon.
    Triggers an autonomous repair run using the same mechanics as the local telemetry loop.
    """
    logger.info(
        f"Received telemetry from namespace={auth_context.namespace} cpu={payload.cpu}% mem={payload.mem}% error_rate={payload.error_rate}"
    )

    # Build a minimal GraphRunRequest – we don't have a specific target file, use a placeholder.
    run_req = GraphRunRequest(
        target_file="system_metrics",
        logs=payload.logs,
        project_path="",
        reproduction_command="",
    )

    # Dispatch repair in background so webhook returns quickly.
    background_tasks.add_task(
        execute_repair,
        app=request.app,
        target_file=run_req.target_file,
        logs=run_req.logs,
        run_id="telemetry_" + str(uuid.uuid4()),
        event_source="daemon/telemetry",
        project_path=run_req.project_path,
        reproduction_command=run_req.reproduction_command,
    )
    return {"status": "accepted", "message": "Telemetry processed, repair cycle queued."}
