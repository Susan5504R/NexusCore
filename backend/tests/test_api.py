import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "dependencies" in data

def test_graph_run_endpoint(patch_services):
    payload = {
        "target_file": "test.py",
        "logs": ["FATAL ERROR"]
    }
    # TestClient is synchronous but correctly handles async endpoints in FastAPI
    response = client.post("/api/v1/graph/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "run_id" in data
    assert "final_exit_code" in data
    # Because of our mocked sandbox, it will return exit code 0
    assert data["final_exit_code"] == 0
    assert data["security_clearance"] is True

def test_graph_run_stream_endpoint(patch_services):
    payload = {
        "target_file": "test.py",
        "logs": ["FATAL ERROR"]
    }
    response = client.post("/api/v1/graph/run/stream", json=payload)
    
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    
    # Inspect the raw text of the SSE output
    text_output = response.text
    
    # Check that events are properly formatted and emitted
    assert "event: node_update" in text_output
    assert "event: complete" in text_output
    assert "active_node" in text_output
    assert "evaluation_node" in text_output

def test_anomaly_trigger(patch_services):
    payload = {
        "alert_id": "TEST-123",
        "service_name": "payment-api",
        "target_file": "payments.py",
        "logs": ["Timeout connecting to DB"]
    }
    response = client.post("/api/v1/anomaly/trigger", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["alert_id"] == "TEST-123"
