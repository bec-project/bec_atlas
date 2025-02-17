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
def test_get_deployment_credentials(logged_in_client):
    """
    Test that the deployment credentials endpoint returns a token.
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
    Test that the refresh deployment credentials endpoint returns a new token.
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


@pytest.mark.timeout(60)
def test_deployment_credential_rejects_unauthorized_user(backend):
    """
    Test that the deployment credentials endpoint returns a 403
    when the user is not authorized.
    """
    client, _ = backend
    response = client.post(
        "/api/v1/user/login", json={"username": "jane.doe@bec_atlas.ch", "password": "atlas"}
    )
    assert response.status_code == 200
    token = response.json()
    assert isinstance(token, str)
    assert len(token) > 20

    deployments = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    response = client.get("/api/v1/deploymentCredentials", params={"deployment_id": deployment_id})
    assert response.status_code == 403
    assert response.json() == {"detail": "User does not have permission to access this resource."}


@pytest.mark.timeout(60)
def test_refresh_deployment_credentials_rejects_unauthorized_user(backend):
    """
    Test that the refresh deployment credentials endpoint returns a 403
    when the user is not authorized.
    """
    client, _ = backend
    response = client.post(
        "/api/v1/user/login", json={"username": "jane.doe@bec_atlas.ch", "password": "atlas"}
    )
    assert response.status_code == 200
    token = response.json()
    assert isinstance(token, str)
    assert len(token) > 20

    deployments = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    response = client.post(
        "/api/v1/deploymentCredentials/refresh", params={"deployment_id": deployment_id}
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "User does not have permission to access this resource."}


@pytest.mark.timeout(60)
def test_get_deployment_credentials_wrong_id(logged_in_client):
    """
    Test that the deployment credentials endpoint returns a 400
    when the deployment ID is invalid.
    """
    client = logged_in_client

    response = client.get("/api/v1/deploymentCredentials", params={"deployment_id": "wrong_id"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid deployment ID"}


@pytest.mark.timeout(60)
def test_deployment_credentials_refresh_not_found(logged_in_client):
    """
    Test that the deployment credentials refresh endpoint returns a 404
    when the deployment is not found.
    """
    client = logged_in_client

    response = client.post(
        "/api/v1/deploymentCredentials/refresh",
        params={"deployment_id": "678aa8d4875568640bd92000"},
    )
    assert response.status_code == 404
    out = response.json()
    assert out == {"detail": "Deployment not found"}
