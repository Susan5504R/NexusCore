import argparse
import time
import requests
import psutil
import sys

def main():
    parser = argparse.ArgumentParser(description="NexusCore SaaS Client Daemon")
    parser.add_argument("--api-key", required=True, help="Your nx_core_ API key")
    parser.add_argument("--server-url", required=True, help="The Render backend URL")
    args = parser.parse_args()

    print(f"🚀 Starting NexusCore Daemon...")
    print(f"🔗 Connected to: {args.server_url}")
    print("Press Ctrl+C to stop.\n")
    
    while True:
        try:
            # Gather local host metrics using psutil
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent
            
            payload = {
                "cpu": cpu,
                "mem": mem,
                "error_rate": 0.0,
                "logs": ["NexusCore daemon health check ping."]
            }
            
            res = requests.post(
                f"{args.server_url}/api/v1/telemetry/ingest",
                json=payload,
                headers={"Authorization": f"Bearer {args.api_key}"},
                timeout=5
            )
            if res.ok:
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
