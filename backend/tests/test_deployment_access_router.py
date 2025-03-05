from unittest import mock

import pytest

from bec_atlas.model.model import DeploymentAccess


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


def test_deployment_access_router_invalid_deployment_id(logged_in_client):
    """
    Test that the deployment access endpoint returns a 400 when the deployment id is invalid.
    """
    response = logged_in_client.get("/api/v1/deployment_access", params={"deployment_id": "test"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid deployment ID"}


def test_deployment_access_router(logged_in_client):
    """
    Test that the deployment access endpoint returns a 200 when the deployment id is valid.
    """
    deployments = logged_in_client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    response = logged_in_client.get(
        "/api/v1/deployment_access", params={"deployment_id": deployment_id}
    )
    assert response.status_code == 200
    out = response.json()
    out = DeploymentAccess(**out)


def test_patch_deployment_access(logged_in_client, backend):
    """
    Test that the deployment access endpoint returns a 200 when the deployment id is valid.
    """
    _, app = backend
    deployments = logged_in_client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    response = logged_in_client.get(
        "/api/v1/deployment_access", params={"deployment_id": deployment_id}
    )
    assert response.status_code == 200
    out = response.json()
    out = DeploymentAccess(**out)

    with mock.patch.object(app.deployment_access_router, "_is_valid_user", return_value=True):
        response = logged_in_client.patch(
            "/api/v1/deployment_access",
            params={"deployment_id": deployment_id},
            json={
                "user_read_access": ["test1"],
                "user_write_access": ["test2"],
                "su_read_access": ["test3"],
                "su_write_access": ["test4"],
                "remote_read_access": ["test5"],
                "remote_write_access": ["test6"],
            },
        )
    assert response.status_code == 200
    out = response.json()
    out = DeploymentAccess(**out)
    assert out.user_read_access == ["test1"]
    assert out.user_write_access == ["test2"]
    assert out.su_read_access == ["test3"]
    assert out.su_write_access == ["test4"]
    assert out.remote_read_access == ["test5"]
    assert out.remote_write_access == ["test6"]

    for user in ["test1", "test2", "test3", "test4"]:
        out = logged_in_client.get(
            "/api/v1/bec_access", params={"deployment_id": deployment_id, "user": user}
        )
        assert out.status_code == 200
        out = out.json()
        assert "token" in out

    for user in ["test5", "test6"]:
        out = logged_in_client.get(
            "/api/v1/bec_access", params={"deployment_id": deployment_id, "user": user}
        )
        assert out.status_code == 404

    # Test that the access can also be retrieved directly
    client, _ = backend
    client.post("/api/v1/user/logout")
    response = client.post(
        "/api/v1/bec_access_login",
        json={"username": "admin@bec_atlas.ch", "password": "admin"},
        params={"deployment_id": deployment_id, "user": "test1"},
    )
    assert response.status_code == 200
    out = response.json()
    assert "token" in out
