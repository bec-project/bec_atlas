import os
import socket

import pytest
from bec_atlas.main import AtlasApp
from bec_atlas.utils.setup_database import setup_database
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def scylla_container(docker_ip, docker_services):
    host = docker_ip
    if os.path.exists("/.dockerenv"):
        # if we are running in the CI, scylla was started as 'scylla' service
        host = "scylla"
    if docker_services is None:
        port = 9042
    else:
        port = docker_services.port_for("scylla", 9042)

    setup_database(host=host, port=port)
    return host, port


@pytest.fixture(scope="session")
def client(scylla_container):
    host, port = scylla_container
    config = {"scylla": {"hosts": [(host, port)]}}

    with TestClient(AtlasApp(config).app) as _client:
        yield _client


@pytest.mark.timeout(60)
def test_login(client):
    """
    Test that the login endpoint returns a token.
    """
    response = client.post(
        "/api/v1/user/login", json={"username": "admin@bec_atlas.ch", "password": "admin"}
    )
    assert response.status_code == 200
    token = response.json()
    assert isinstance(token, str)
    assert len(token) > 20


@pytest.mark.timeout(60)
def test_login_wrong_password(client):
    """
    Test that the login returns a 401 when the password is wrong.
    """
    response = client.post(
        "/api/v1/user/login", json={"username": "admin@bec_atlas.ch", "password": "wrong_password"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid password"}


@pytest.mark.timeout(60)
def test_login_unknown_user(client):
    """
    Test that the login returns a 404 when the user is unknown.
    """
    response = client.post(
        "/api/v1/user/login",
        json={"username": "no_user@bec_atlas.ch", "password": "wrong_password"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
