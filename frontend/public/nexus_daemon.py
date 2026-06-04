import argparse
import time
import subprocess
import requests
import psutil
import sys

def main():
    parser = argparse.ArgumentParser(description="NexusCore SaaS Client Daemon")
    parser.add_argument("--api-key", required=True, help="Your nx_core_ API key")
    parser.add_argument("--server-url", required=True, help="The Render backend URL")
    parser.add_argument(
        "--simulate-anomaly",
        action="store_true",
        help="Send a single fake anomaly with crash logs, then resume normal pings.",
    )
    parser.add_argument(
        "--watch",
        type=str,
        default=None,
        help="A command to monitor, e.g. 'python buggy_data_processor.py'. "
             "If it crashes, the daemon captures stderr and sends it as an anomaly.",
    )
    args = parser.parse_args()

    print("🚀 Starting NexusCore Daemon...")
    print(f"🔗 Connected to: {args.server_url}")
    if args.watch:
        print(f"👁️  Watching command: {args.watch}")
    print("Press Ctrl+C to stop.\n")

    anomaly_sent = False

    # ── If --watch is set, run the command first and capture any crash ──
    watched_crash_logs = None
    if args.watch:
        print(f"▶️  Executing: {args.watch}")
        try:
            result = subprocess.run(
                args.watch,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                stderr_lines = [
                    line for line in result.stderr.strip().splitlines() if line.strip()
                ]
                if stderr_lines:
                    watched_crash_logs = stderr_lines
                    print(f"💥 Command crashed with exit code {result.returncode}!")
                    print(f"   Captured {len(stderr_lines)} lines of stderr.")
                    print("   Will send as anomaly on next telemetry cycle.\n")
                else:
                    print(f"⚠️  Command exited with code {result.returncode} but no stderr output.\n")
            else:
                print("✅ Command ran successfully — no anomaly detected.\n")
        except subprocess.TimeoutExpired:
            watched_crash_logs = ["Process timed out after 30 seconds (possible hang/deadlock)."]
            print("⏰ Command timed out — treating as anomaly.\n")
        except Exception as e:
            print(f"[WARNING] Failed to run watched command: {e}\n")

    while True:
        try:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent

            # Priority 1: Send watched crash logs as anomaly
            if watched_crash_logs and not anomaly_sent:
                print("🚨 SENDING ANOMALY — crash logs from watched command...")
                payload = {
                    "cpu": cpu,
                    "mem": mem,
                    "error_rate": 1.0,
                    "logs": watched_crash_logs,
                }
                anomaly_sent = True

            # Priority 2: --simulate-anomaly flag
            elif args.simulate_anomaly and not anomaly_sent:
                print("\n🚨 SIMULATING ANOMALY — sending spike + crash logs...")
                payload = {
                    "cpu": 98.5,
                    "mem": 94.2,
                    "error_rate": 0.85,
                    "logs": [
                        "Traceback (most recent call last):",
                        '  File "buggy_data_processor.py", line 19, in process_data',
                        "    total_age += user['age']",
                        "TypeError: unsupported operand type(s) for +=: 'int' and 'str'",
                    ],
                }
                anomaly_sent = True

            # Normal telemetry
            else:
                payload = {
                    "cpu": cpu,
                    "mem": mem,
                    "error_rate": 0.0,
                    "logs": [],
                }

            res = requests.post(
                f"{args.server_url}/api/v1/telemetry/ingest",
                json=payload,
                headers={"Authorization": f"Bearer {args.api_key}"},
                timeout=10,
            )
            if res.ok:
                data = res.json()
                status = data.get("status", "ok")
                if status == "anomaly_detected":
                    run_id = data.get("run_id", "unknown")
                    print(f"🚨 [ANOMALY] Backend queued autonomous repair! run_id={run_id}")
                else:
                    print(f"[OK] Telemetry sent | CPU: {cpu}% | RAM: {mem}%")
            else:
                print(f"[ERROR] Backend rejected telemetry: {res.status_code} - {res.text}")

        except Exception as e:
            print(f"[WARNING] Failed to connect to backend: {e}")

        time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down daemon.")
        sys.exit(0)
