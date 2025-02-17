import pytest


@pytest.fixture
def logged_in_client(backend):
    client, _ = backend
    response = client.post(
        "/api/v1/user/login", json={"username": "admin@bec_atlas.ch", "password": "admin"}
    )
    assert response.status_code == 200
    token = response.json()
    assert isinstance(token, str)
    assert len(token) > 20
    return client


@pytest.mark.timeout(60)
@pytest.mark.parametrize("realm, num_deployments", [("test", 0), ("demo_beamline_1", 1)])
def test_get_deployment_by_realm(logged_in_client, realm, num_deployments):
    """
    Test that the login endpoint returns a token.
    """
    client = logged_in_client
    response = client.get("/api/v1/deployments/realm", params={"realm": realm})
    assert response.status_code == 200
    deployments = response.json()
    assert len(deployments) == num_deployments


@pytest.mark.timeout(60)
def test_get_deployment_by_id(logged_in_client):
    """
    Test that the login endpoint returns a token.
    """
    client = logged_in_client

    deployments = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    response = client.get("/api/v1/deployments/id", params={"deployment_id": deployment_id})
    assert response.status_code == 200
    deployment = response.json()
    assert deployment["_id"] == deployment_id
    assert deployment["realm_id"] == "demo_beamline_1"


@pytest.mark.timeout(60)
def test_get_deployment_by_id_wrong_id(logged_in_client):
    """
    Test that the login endpoint returns a token.
    """
    client = logged_in_client

    response = client.get("/api/v1/deployments/id", params={"deployment_id": "wrong_id"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid deployment id"}
