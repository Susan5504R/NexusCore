import asyncio
import psutil
import logging
import random
from fastapi import FastAPI

from app.anomaly.detector import AnomalyDetector
from app.core.schemas import new_agent_state, OperationalLogEntry
from app.graph.orchestrator import create_sre_orchestrator

logger = logging.getLogger("nexuscore.anomaly.telemetry")
detector = AnomalyDetector(contamination=0.05)

async def run_healing_cycle(app: FastAPI, orchestrator, state: dict):
    """
    Executes the autonomous repair graph triggered by an internal anomaly.
    """
    logger.info("🧠 Proactive telemetry-triggered repair cycle started.")
    try:
        final_state = await orchestrator.ainvoke(state)
        
        # Log to durable operational ledger
        ledger = getattr(app.state, "ledger", None)
        if ledger:
            exit_code = final_state.get("execution_exit_code", -1)
            status = "success" if exit_code == 0 else "failed"
            if not final_state.get("security_clearance", False):
                status = "blocked_security"
                
            entry = OperationalLogEntry(
                event_source="background/telemetry",
                agent_action="proactive_healing",
                execution_payload="Automated PyOD Anomaly response",
                execution_status=status
            )
            await ledger.log_event(entry)
            
    except Exception as e:
        logger.error(f"Proactive healing cycle crashed: {e}", exc_info=True)

async def telemetry_loop(app: FastAPI):
    """
    Background worker that continuously samples system metrics.
    When the Isolation Forest flags an anomaly, it fires the repair graph.
    """
    logger.info("Starting background telemetry loop (PyOD IForest)...")
    
    # We instantiate a local orchestrator since we are outside the request context
    orchestrator = create_sre_orchestrator()
    
    # Initial CPU read to prime psutil
    psutil.cpu_percent(interval=None)
    
    while True:
        try:
            # 1. Sample physical metrics
            cpu_usage = psutil.cpu_percent(interval=None)
            mem_usage = psutil.virtual_memory().percent
            
            # 2. Simulate error rate (In production, read from a log aggregator)
            error_rate = random.uniform(0.0, 1.0)
            
            # 1% chance to simulate a massive failure spike for demonstration
            if random.random() < 0.01: 
                error_rate = 99.9
                cpu_usage = 100.0
                
            # 3. Feed 3D vector into PyOD
            is_anomaly = detector.add_data_point(cpu_usage, mem_usage, error_rate)
            
            if is_anomaly:
                logger.warning(f"🚨 ANOMALY DETECTED! CPU: {cpu_usage}%, Mem: {mem_usage}%, Err: {error_rate}")
                
                # 4. Trigger self-healing
                logs = [f"SYSTEM ANOMALY TRIPPED: High resource exhaustion or error rate detected. CPU={cpu_usage}, Mem={mem_usage}, ErrRate={error_rate}"]
                
                state = new_agent_state(
                    current_target_file="system_metrics", 
                    discovered_logs=logs
                )
                
                # Run graph without awaiting so telemetry loop isn't blocked
                asyncio.create_task(run_healing_cycle(app, orchestrator, state))
                
                # Sleep a bit longer after firing to avoid trigger storms
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Telemetry loop error: {e}")
            
        # Sample every 2 seconds
        await asyncio.sleep(2)
