import httpx
import json

def test_stream():
    url = "http://127.0.0.1:8000/api/v1/graph/run/stream"
    payload = {
        "target_file": "server.py",
        "logs": ["FATAL CRASH: ZeroDivisionError"]
    }
    
    print(f"Connecting to {url}...")
    try:
        with httpx.stream("POST", url, json=payload, timeout=60.0) as r:
            print("Connected! Listening for Server-Sent Events...\n")
            for line in r.iter_lines():
                if line:
                    print(line)
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_stream()
