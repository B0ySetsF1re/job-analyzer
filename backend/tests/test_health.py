from fastapi.testclient import TestClient


def test_health_returns_ok_and_env(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "env": "test"}
