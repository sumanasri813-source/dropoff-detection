import pytest
from src.api.app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    """Test that the health endpoint returns correctly."""
    response = client.get("/health")
    assert response.status_code in [200, 503]
    json_data = response.get_json()
    assert "status" in json_data
    assert "health" in json_data

def test_predict_validation(client):
    """Test that predicting without a payload returns a 400 validation error."""
    response = client.post("/predict", json={})
    assert response.status_code == 400
    json_data = response.get_json()
    assert "error" in json_data

def test_swagger_docs(client):
    """Test that the interactive Swagger UI is available."""
    response = client.get("/apidocs/")
    assert response.status_code == 200
