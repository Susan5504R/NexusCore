import argparse
import time
import subprocess
import requests
import psutil
import sys
import os
import threading
from collections import deque

class DaemonCircuitBreaker:
    def __init__(self, max_failures=3, time_window=60):
        self.max_failures = max_failures
        self.time_window = time_window
        self.failure_timestamps = []

    def record_failure(self):
        now = time.time()
        self.failure_timestamps.append(now)
        self.failure_timestamps = [t for t in self.failure_timestamps if now - t <= self.time_window]

    def is_open(self):
        now = time.time()
        self.failure_timestamps = [t for t in self.failure_timestamps if now - t <= self.time_window]
        return len(self.failure_timestamps) >= self.max_failures

    def reset(self):
        self.failure_timestamps.clear()

class ProcessSupervisor:
    def __init__(self, command: str):
        self.command = command
        self.process = None
        self.stderr_lines = deque(maxlen=100)
        self._stop_event = threading.Event()
        self.crashed = False

    def start(self):
        self.crashed = False
        self._stop_event.clear()
        self.stderr_lines.clear()
        print(f"▶️  Starting supervised process: {self.command}")
        
        self.process = subprocess.Popen(
            self.command,
            shell=True,
            stdout=subprocess.DEVNULL, # Focus on errors for anomalies
            stderr=subprocess.PIPE,
            text=True
        )
        
        def _read_stderr():
            for line in self.process.stderr:
                if line.strip():
                    self.stderr_lines.append(line.strip())
            
            self.process.wait()
            if self.process.returncode != 0 and not self._stop_event.is_set():
                self.crashed = True
                print(f"\n💥 Supervised process crashed with exit code {self.process.returncode}!")
        
        self.monitor_thread = threading.Thread(target=_read_stderr, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        self._stop_event.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        print("🛑 Supervised process stopped.")

    def restart(self, new_command=None):
        if new_command:
            self.command = new_command
        self.stop()
        self.start()

    def get_crash_logs(self):
        if self.crashed:
            logs = list(self.stderr_lines)
            self.crashed = False
            self.stderr_lines.clear()
            return logs
        return None

def apply_patch(project_dir: str, target_file: str, patch_code: str) -> bool:
    if not project_dir:
        print("❌ Cannot apply patch: --project-dir not provided.")
        return False
        
    rel_path = target_file
    if os.path.isabs(rel_path):
        rel_path = os.path.relpath(rel_path, project_dir)
        if rel_path.startswith(".."):
            basename = os.path.basename(target_file)
            rel_path = basename

    target_path = os.path.join(project_dir, rel_path)
    
    if not os.path.abspath(target_path).startswith(os.path.abspath(project_dir)):
        print(f"❌ Security violation: Path {target_path} is outside project dir!")
        return False

    if not os.path.exists(target_path):
        basename = os.path.basename(rel_path)
        found = False
        for root, _, files in os.walk(project_dir):
            if basename in files:
                target_path = os.path.join(root, basename)
                found = True
                break
        if not found:
            print(f"❌ Could not locate file {basename} in project directory.")
            return False

    try:
        backup_path = f"{target_path}.bak"
        if os.path.exists(target_path):
            with open(target_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
                
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(patch_code)
        print(f"✅ Applied patch to {target_path} (backup saved as .bak)")
        return True
    except Exception as e:
        print(f"❌ Failed to write patch: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="NexusCore SaaS Bidirectional Daemon")
    parser.add_argument("--api-key", required=True, help="Your nx_core_ API key")
    parser.add_argument("--server-url", required=True, help="The Render backend URL")
    parser.add_argument("--project-dir", type=str, help="Absolute path to the user's local project directory (needed for patching)")
    parser.add_argument("--watch", type=str, help="A command to monitor, e.g. 'python buggy_script.py'")
    parser.add_argument("--simulate-anomaly", action="store_true", help="Send a fake anomaly on startup.")
    parser.add_argument("--no-auto-restart", action="store_true", help="Apply patch but do not restart watched process.")
    args = parser.parse_args()

    print("🚀 Starting NexusCore Daemon...")
    print(f"🔗 Connected to: {args.server_url}")
    if args.project_dir:
        print(f"📁 Project Dir: {args.project_dir}")
    else:
        print("⚠️  No --project-dir provided. Daemon will report telemetry but cannot apply patches.")
    
    supervisor = None
    circuit_breaker = DaemonCircuitBreaker()
    
    if args.watch:
        supervisor = ProcessSupervisor(args.watch)
        supervisor.start()

    print("Press Ctrl+C to stop.\n")

    anomaly_sent = False
    
    while True:
        try:
            # 1. Gather Telemetry
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent
            logs_to_send = []

            # 2. Check for process crash
            if supervisor:
                crash_logs = supervisor.get_crash_logs()
                if crash_logs:
                    circuit_breaker.record_failure()
                    if circuit_breaker.is_open():
                        print("\n🔴 [CIRCUIT BREAKER OPEN] Too many crashes in 60s! Manual intervention required. Suppressing further anomalies.")
                    else:
                        print("\n🚨 SENDING ANOMALY — crash logs from watched command...")
                        logs_to_send = crash_logs
                        anomaly_sent = True

            # Fake anomaly fallback
            if args.simulate_anomaly and not anomaly_sent and not logs_to_send:
                print("\n🚨 SIMULATING ANOMALY — sending spike + crash logs...")
                logs_to_send = [
                    "Traceback (most recent call last):",
                    '  File "buggy_data_processor.py", line 19, in process_data',
                    "TypeError: unsupported operand type(s) for +=: 'int' and 'str'",
                ]
                anomaly_sent = True

            # Extract target file from crash traceback if available
            crashed_file = ""
            if logs_to_send:
                import re
                file_matches = re.findall(r'File "([^"]+)"', "\n".join(logs_to_send))
                if file_matches:
                    crashed_file = os.path.basename(file_matches[-1])

            payload = {
                "cpu": 98.5 if logs_to_send else cpu,
                "mem": 94.2 if logs_to_send else mem,
                "error_rate": 1.0 if logs_to_send else 0.0,
                "logs": logs_to_send,
                "reproduction_command": (args.watch or "") if logs_to_send else "",
                "target_file": crashed_file,
            }

            # 3. Send Telemetry
            headers = {"Authorization": f"Bearer {args.api_key}"}
            res = requests.post(f"{args.server_url}/api/v1/telemetry/ingest", json=payload, headers=headers, timeout=5)
            if res.ok:
                data = res.json()
                if data.get("status") == "anomaly_detected":
                    print(f"\n🚨 [ANOMALY] Backend queued autonomous repair! run_id={data.get('run_id')}")
                elif not logs_to_send:
                    sys.stdout.write(f"\r[OK] Telemetry sent | CPU: {cpu}% | RAM: {mem}%  ")
                    sys.stdout.flush()
            else:
                print(f"\n[ERROR] Backend rejected telemetry: {res.status_code}")

            # 4. Poll for Patches
            if args.project_dir:
                poll_res = requests.get(f"{args.server_url}/api/v1/deployments/pending", headers=headers, timeout=5)
                if poll_res.ok:
                    patches = poll_res.json().get("patches", [])
                    for patch in patches:
                        print(f"\n📦 Received patch {patch['patch_id']} from cloud!")
                        
                        success = apply_patch(args.project_dir, patch["target_file"], patch["patch_code"])
                        
                        status = "failed"
                        stderr_msg = ""
                        if success:
                            status = "applied"
                            if supervisor and not args.no_auto_restart:
                                if circuit_breaker.is_open():
                                    print("🔴 Circuit breaker is OPEN. Skipping auto-restart.")
                                    status = "circuit_breaker_open"
                                    stderr_msg = "Daemon circuit breaker open. Too many crashes."
                                else:
                                    print("🔄 Restarting watched process...")
                                    new_cmd = patch.get("reproduction_command") or supervisor.command
                                    supervisor.restart(new_cmd)
                                    
                                    # Brief health check to see if it immediately crashes
                                    time.sleep(3)
                                    if supervisor.crashed:
                                        print("❌ Process crashed immediately after restart!")
                                        status = "unhealthy"
                                        crash_logs = supervisor.get_crash_logs()
                                        stderr_msg = "\n".join(crash_logs) if crash_logs else "Unknown crash"
                                        circuit_breaker.record_failure()
                                    else:
                                        print("✅ Process verified healthy.")
                                        status = "restarted"
                                        circuit_breaker.reset()

                        ack_payload = {"patch_id": patch["patch_id"], "status": status, "stderr": stderr_msg}
                        ack_res = requests.post(f"{args.server_url}/api/v1/deployments/ack", json=ack_payload, headers=headers, timeout=5)
                        if ack_res.ok:
                            print(f"📡 Acknowledged patch {patch['patch_id']} as {status}")
                
        except requests.exceptions.RequestException as e:
            pass # Suppress noisy connection errors if server is down temporarily
        except Exception as e:
            print(f"\n[WARNING] Daemon loop error: {e}")

        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down daemon.")
        sys.exit(0)
