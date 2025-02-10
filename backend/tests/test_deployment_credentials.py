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
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.mark.timeout(60)
def test_get_deployment_credentials(logged_in_client):
    """
    Test that the login endpoint returns a token.
    """
    client = logged_in_client

    deployments = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    response = client.get("/api/v1/deploymentCredentials", params={"deployment_id": deployment_id})
    assert response.status_code == 200


@pytest.mark.timeout(60)
def test_refresh_deployment_credentials(logged_in_client):
    """
    Test that the login endpoint returns a token.
    """
    client = logged_in_client

    deployments = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    old_token = client.get(
        "/api/v1/deploymentCredentials", params={"deployment_id": deployment_id}
    ).json()["credential"]

    response = client.post(
        "/api/v1/deploymentCredentials/refresh", params={"deployment_id": deployment_id}
    )
    assert response.status_code == 200
    out = response.json()
    assert out == {"_id": deployment_id, "credential": out["credential"]}
    assert out["credential"] != old_token
