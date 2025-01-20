import pytest


@pytest.fixture
def backend_client(backend):
    client, _ = backend
    return client


@pytest.mark.timeout(60)
def test_login(backend_client):
    """
    Test that the login endpoint returns a token.
    """
    response = backend_client.post(
        "/api/v1/user/login", json={"username": "admin@bec_atlas.ch", "password": "admin"}
    )
    assert response.status_code == 200
    token = response.json()
    assert isinstance(token, str)
    assert len(token) > 20


@pytest.mark.timeout(60)
def test_login_wrong_password(backend_client):
    """
    Test that the login returns a 401 when the password is wrong.
    """
    response = backend_client.post(
        "/api/v1/user/login", json={"username": "admin@bec_atlas.ch", "password": "wrong_password"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "User not found or password is incorrect"}


@pytest.mark.timeout(60)
def test_login_unknown_user(backend_client):
    """
    Test that the login returns a 401 when the user is unknown.
    """
    response = backend_client.post(
        "/api/v1/user/login",
        json={"username": "no_user@bec_atlas.ch", "password": "wrong_password"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "User not found or password is incorrect"}
