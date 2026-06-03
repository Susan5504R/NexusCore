"""API / integration tests using FastAPI's TestClient against a mocked stack."""


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "dependencies" in data


def test_graph_run_endpoint(client):
    payload = {"target_file": "test.py", "logs": ["FATAL ERROR"]}
    response = client.post("/api/v1/graph/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "run_id" in data
    assert "final_exit_code" in data
    # The mocked sandbox returns exit code 0, and the mocked arbiter clears it.
    assert data["final_exit_code"] == 0
    assert data["security_clearance"] is True


def test_graph_run_stream_endpoint(client):
    payload = {"target_file": "test.py", "logs": ["FATAL ERROR"]}
    response = client.post("/api/v1/graph/run/stream", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    text_output = response.text
    assert "event: node_update" in text_output
    assert "event: complete" in text_output
    assert "active_node" in text_output
    assert "evaluation_node" in text_output


def test_anomaly_trigger(client):
    payload = {
        "alert_id": "TEST-123",
        "service_name": "payment-api",
        "target_file": "payments.py",
        "logs": ["Timeout connecting to DB"],
    }
    response = client.post("/api/v1/anomaly/trigger", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["alert_id"] == "TEST-123"
