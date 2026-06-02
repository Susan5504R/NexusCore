import asyncio
import psutil
import logging
import random
import uuid
from fastapi import FastAPI

from app.anomaly.detector import AnomalyDetector
from app.services.graph_runner import execute_repair

logger = logging.getLogger("nexuscore.anomaly.telemetry")
detector = AnomalyDetector(contamination=0.05)

async def telemetry_loop(app: FastAPI):
    """
    Background worker that continuously samples system metrics.
    When the Isolation Forest flags an anomaly, it fires the repair graph.
    """
    logger.info("Starting background telemetry loop (PyOD IForest)...")
    
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
                run_id = str(uuid.uuid4())
                
                logger.info("🧠 Proactive telemetry-triggered repair cycle started.")
                
                # Run graph without awaiting so telemetry loop isn't blocked
                asyncio.create_task(
                    execute_repair(
                        app=app,
                        target_file="system_metrics",
                        logs=logs,
                        run_id=run_id,
                        event_source="background/telemetry"
                    )
                )
                
                # Sleep a bit longer after firing to avoid trigger storms
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Telemetry loop error: {e}")
            
        # Sample every 2 seconds
        await asyncio.sleep(2)
