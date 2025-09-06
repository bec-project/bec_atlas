import socket

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


@pytest.mark.timeout(60)
def test_download_env_file(logged_in_client):
    """
    Test that the environment file download endpoint returns a properly formatted .env file.
    """
    client = logged_in_client

    deployments = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment = deployments[0]
    deployment_id = deployment["_id"]
    deployment_name = deployment["name"]

    response = client.get(
        "/api/v1/deploymentCredentials/env", params={"deployment_name": deployment_name}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert "Content-Disposition" in response.headers
    assert ".env" in response.headers["Content-Disposition"]

    # Check the content format
    content = response.text
    lines = content.strip().split("\n")
    assert len(lines) == 3
    assert lines[0].startswith("ATLAS_HOST=")
    assert lines[1] == f"ATLAS_DEPLOYMENT={deployment_id}"
    assert lines[2].startswith("ATLAS_KEY=")

    # Verify the ATLAS_HOST format
    atlas_host_line = lines[0]
    expected_hostname = socket.gethostname()
    assert atlas_host_line.startswith(f"ATLAS_HOST={expected_hostname}:")
    assert ":" in atlas_host_line.split("=")[1]  # Should contain host:port


@pytest.mark.timeout(60)
def test_download_env_file_unauthorized_user(backend):
    """
    Test that the environment file download endpoint returns a 403
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
    deployment_name = deployments[0]["name"]

    response = client.get(
        "/api/v1/deploymentCredentials/env", params={"deployment_name": deployment_name}
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "User does not have permission to access this resource."}


@pytest.mark.timeout(60)
def test_download_env_file_wrong_id(logged_in_client):
    """
    Test that the environment file download endpoint returns a 404
    when the deployment name is invalid.
    """
    client = logged_in_client

    response = client.get(
        "/api/v1/deploymentCredentials/env", params={"deployment_name": "wrong_name"}
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Deployment not found"}


@pytest.mark.timeout(60)
def test_download_env_file_not_found(logged_in_client):
    """
    Test that the environment file download endpoint returns a 404
    when the deployment is not found.
    """
    client = logged_in_client

    response = client.get(
        "/api/v1/deploymentCredentials/env", params={"deployment_name": "nonexistent_deployment"}
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Deployment not found"}
