import pytest
from fastapi.testclient import TestClient
from main import app
client = TestClient(app)
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "AI SQL Generator" in response.json()["message"]
def test_generate_sql():
    response = client.post(
        "/generate_sql/",
        json={
            "question": "Show me all users",
            "database_type": "PostgreSQL"
        }
    )
    assert response.status_code == 200
    assert "SELECT" in response.json()["sql_query"].upper()
def test_health():
    response = client.get("/health")
    assert response.status_code == 200


