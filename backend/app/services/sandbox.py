import os
import tempfile
import asyncio
import logging
from typing import Tuple

import docker

from app.core.config import get_settings

logger = logging.getLogger("nexuscore.sandbox")

import shutil

def run_in_sandbox_sync(
    code: str,
    docker_client: docker.DockerClient = None,
    project_path: str = "",
    reproduction_command: str = "",
    target_file: str = ""
) -> Tuple[int, str, str]:
    """
    Synchronous docker execution. 
    If project_path is provided, copies the project to a temp dir, writes the patch 
    to the target_file in that temp dir, mounts it, installs dependencies from 
    requirements.txt, and runs the reproduction command.
    Otherwise, falls back to running the standalone script.
    """
    settings = get_settings()
    
    try:
        client = docker_client or docker.from_env()
    except Exception as e:
        logger.error(f"Failed to connect to Docker daemon: {e}")
        return -1, "", f"Failed to connect to Docker daemon: {e}"
        
    temp_dir = tempfile.mkdtemp()
    mounts = {}
    container_cmd = []
    working_dir = "/app"

    try:
        if project_path and os.path.exists(project_path):
            # Copy project to temporary directory to avoid mutating the original code
            shutil.copytree(project_path, temp_dir, dirs_exist_ok=True)
            
            # Apply the patch to the target file in the temporary directory
            if target_file:
                # Target file can be absolute or relative to project_path
                rel_target = os.path.relpath(target_file, project_path) if os.path.isabs(target_file) else target_file
                target_dest = os.path.join(temp_dir, rel_target)
                os.makedirs(os.path.dirname(target_dest), exist_ok=True)
                with open(target_dest, 'w', encoding='utf-8') as f:
                    f.write(code)
            
            mounts = {temp_dir: {'bind': '/app/workspace', 'mode': 'rw'}}
            working_dir = "/app/workspace"
            
            # Setup command to install requirements and run reproduction command
            repro_cmd = reproduction_command or "python main.py"
            container_cmd = [
                "/bin/sh", "-c", 
                f"if [ -f requirements.txt ]; then pip install --disable-pip-version-check -r requirements.txt || true; fi; {repro_cmd}"
            ]
        else:
            # Fallback to standalone script execution
            temp_path = os.path.join(temp_dir, "script.py")
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(code)
                
            mounts = {temp_path: {'bind': '/app/script.py', 'mode': 'ro'}}
            container_cmd = ["python", "/app/script.py"]
            
        container = client.containers.run(
            image=settings.sandbox_image,
            command=container_cmd,
            volumes=mounts,
            working_dir=working_dir,
            network_mode=settings.sandbox_network_mode,
            mem_limit=settings.sandbox_mem_limit,
            nano_cpus=settings.sandbox_nano_cpus,
            detach=True,
            remove=False
        )
        
        try:
            result = container.wait(timeout=settings.sandbox_timeout_seconds)
            exit_code = result.get('StatusCode', -1)
            
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
        if 'container' in locals() and container:
            try:
                container.remove(force=True)
            except Exception as e:
                logger.warning(f"Failed to remove container: {e}")
                
        # Cleanup temporary directory
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to remove temporary directory {temp_dir}: {e}")
                
    return exit_code, stdout_str, stderr_str

async def execute_in_sandbox(
    code: str,
    docker_client: docker.DockerClient = None,
    project_path: str = "",
    reproduction_command: str = "",
    target_file: str = ""
) -> Tuple[int, str, str]:
    """
    Async wrapper for sandbox execution to prevent blocking the event loop.
    Returns (exit_code, stdout, stderr).
    """
    logger.info("Dispatching code to Docker sandbox...")
    return await asyncio.to_thread(
        run_in_sandbox_sync,
        code,
        docker_client,
        project_path,
        reproduction_command,
        target_file
    )
