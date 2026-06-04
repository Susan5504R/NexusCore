import argparse
import time
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
    args = parser.parse_args()

    print(f"🚀 Starting NexusCore Daemon...")
    print(f"🔗 Connected to: {args.server_url}")
    print("Press Ctrl+C to stop.\n")

    anomaly_sent = False

    while True:
        try:
            # Gather local host metrics using psutil
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent

            # If --simulate-anomaly and we haven't sent it yet, fire a spike
            if args.simulate_anomaly and not anomaly_sent:
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
                    print(f"🚨 [ANOMALY] Backend queued repair! run_id={data.get('run_id')}")
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
