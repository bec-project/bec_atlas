import pytest


@pytest.fixture
def backend_client(backend):
    client, _ = backend
    return client


@pytest.mark.timeout(20)
def test_health_endpoint_healthy(backend_client):
    """
    Test that the health endpoint returns 200 when both Redis and MongoDB are healthy.
    """
    response = backend_client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "services" in data
    assert "redis" in data["services"]
    assert "mongodb" in data["services"]
    assert data["services"]["redis"]["status"] == "healthy"
    assert data["services"]["mongodb"]["status"] == "healthy"


@pytest.mark.timeout(20)
def test_health_endpoint_structure(backend_client):
    """
    Test that the health endpoint returns the expected JSON structure.
    """
    response = backend_client.get("/api/v1/health")

    data = response.json()

    # Check top-level structure
    assert "status" in data
    assert "services" in data

    # Check services structure
    services = data["services"]
    assert "redis" in services
    assert "mongodb" in services

    # Check each service has required fields
    for service_name, service_data in services.items():
        assert "status" in service_data
        assert "message" in service_data
        assert service_data["status"] in ["healthy", "unhealthy"]
        assert isinstance(service_data["message"], str)
