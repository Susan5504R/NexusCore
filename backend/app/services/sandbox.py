import os
import tempfile
import asyncio
import logging
from typing import Tuple

import docker

from app.core.config import get_settings

logger = logging.getLogger("nexuscore.sandbox")

def run_in_sandbox_sync(code: str, docker_client: docker.DockerClient = None) -> Tuple[int, str, str]:
    """
    Synchronous docker execution. 
    Writes code to a temporary file, mounts it read-only into an ephemeral container,
    executes it with strict resource limits, and captures the output.
    """
    settings = get_settings()
    
    # Use provided client or fallback to a new one
    try:
        client = docker_client or docker.from_env()
    except Exception as e:
        logger.error(f"Failed to connect to Docker daemon: {e}")
        return -1, "", f"Failed to connect to Docker daemon: {e}"
    
    # Create a temporary file to hold the generated script
    fd, temp_path = tempfile.mkstemp(suffix=".py", text=True)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(code)
        
    exit_code = -1
    stdout_str = ""
    stderr_str = ""
    container = None
    
    try:
        container = client.containers.run(
            image=settings.sandbox_image,
            command=["python", "/app/script.py"],
            volumes={temp_path: {'bind': '/app/script.py', 'mode': 'ro'}},
            network_mode=settings.sandbox_network_mode,
            mem_limit=settings.sandbox_mem_limit,
            nano_cpus=settings.sandbox_nano_cpus,
            detach=True,
            remove=False  # Keep it temporarily to extract logs and exit code safely
        )
        
        try:
            # Wait for execution with a hard timeout
            result = container.wait(timeout=settings.sandbox_timeout_seconds)
            exit_code = result.get('StatusCode', -1)
            
            # Fetch logs separately
            stdout = container.logs(stdout=True, stderr=False)
            stderr = container.logs(stdout=False, stderr=True)
            
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
            
        except Exception as wait_exc:
            logger.error(f"Container wait error or timeout: {wait_exc}")
            container.kill()
            exit_code = -1
            stderr_str = f"Execution timed out or failed to wait: {wait_exc}"
            
    except docker.errors.ImageNotFound:
        logger.error(f"Sandbox image {settings.sandbox_image} not found.")
        return -1, "", f"Sandbox image '{settings.sandbox_image}' not found locally. Please run 'docker pull {settings.sandbox_image}'."
    except Exception as e:
        logger.error(f"Sandbox execution failed: {e}")
        return -1, "", str(e)
    finally:
        # Cleanup container
        if container:
            try:
                container.remove(force=True)
            except Exception as e:
                logger.warning(f"Failed to remove container: {e}")
                
        # Cleanup temporary file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {temp_path}: {e}")
                
    return exit_code, stdout_str, stderr_str

async def execute_in_sandbox(code: str, docker_client: docker.DockerClient = None) -> Tuple[int, str, str]:
    """
    Async wrapper for sandbox execution to prevent blocking the event loop.
    Returns (exit_code, stdout, stderr).
    """
    logger.info("Dispatching code to Docker sandbox...")
    return await asyncio.to_thread(run_in_sandbox_sync, code, docker_client)
