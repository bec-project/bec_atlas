import json

import pytest
from bson import ObjectId


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


def _get_session(client):
    deployments = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    response = client.get("/api/v1/sessions", params={"deployment_id": deployment_id})
    assert response.status_code == 200

    session_id = response.json()[0]["_id"]
    return session_id


@pytest.mark.timeout(60)
def test_get_scans_for_session(logged_in_client):
    """
    Test that the scans/sessions endpoint returns the correct number of scans.
    """
    client = logged_in_client

    session_id = _get_session(client)

    response = client.get("/api/v1/scans/session", params={"session_id": session_id})

    assert response.status_code == 200
    scans = response.json()
    assert len(scans) == 3

    # this endpoint should enforce the session_id as param
    response = client.get("/api/v1/scans/session")
    assert response.status_code == 422


@pytest.mark.timeout(60)
def test_get_scans_for_session_wrong_id(logged_in_client):
    """
    Test that the scans/sessions endpoint returns 400 for a wrong session id.
    """
    client = logged_in_client

    response = client.get("/api/v1/scans/session", params={"session_id": "wrong_id"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid session ID"}


@pytest.mark.timeout(60)
def test_get_scans_for_session_with_filter(logged_in_client):
    """
    Test that the scans/sessions endpoint returns the correct number of scans with a filter.
    """
    client = logged_in_client

    session_id = _get_session(client)

    response = client.get(
        "/api/v1/scans/session",
        params={"session_id": session_id, "filter": '{"scan_number": 2251}'},
    )

    assert response.status_code == 200
    scans = response.json()
    assert len(scans) == 1
    assert scans[0]["scan_number"] == 2251


@pytest.mark.timeout(60)
def test_get_scans_for_session_with_fields(logged_in_client):
    """
    Test that the scans/session endpoint returns the correct fields.
    """
    client = logged_in_client

    session_id = _get_session(client)

    response = client.get(
        "/api/v1/scans/session", params={"session_id": session_id, "fields": ["scan_number"]}
    )

    assert response.status_code == 200
    scans = response.json()
    assert len(scans) == 3
    assert "scan_number" in scans[0]
    assert "num_points" not in scans[0]


@pytest.mark.timeout(60)
def test_get_scans_for_session_with_offset_limit(logged_in_client):
    """
    Test that the scans/session endpoint returns the correct number of scans with offset and limit.
    """
    client = logged_in_client

    session_id = _get_session(client)

    response = client.get(
        "/api/v1/scans/session", params={"session_id": session_id, "offset": 0, "limit": 1}
    )

    assert response.status_code == 200
    scans = response.json()
    assert len(scans) == 1
    assert scans[0]["scan_number"] == 2251

    response = client.get(
        "/api/v1/scans/session", params={"session_id": session_id, "offset": 1, "limit": 1}
    )

    assert response.status_code == 200
    scans = response.json()
    assert len(scans) == 1
    assert scans[0]["scan_number"] == 2252


@pytest.mark.timeout(60)
def test_get_scans_for_session_with_sort(logged_in_client):
    """
    Test that the scans/session endpoint returns the correct number of scans with sort.
    """
    client = logged_in_client

    session_id = _get_session(client)

    response = client.get(
        "/api/v1/scans/session", params={"session_id": session_id, "sort": '{"scan_number": 1}'}
    )

    assert response.status_code == 200
    scans = response.json()
    assert len(scans) == 3
    assert scans[0]["scan_number"] == 2251
    assert scans[1]["scan_number"] == 2252
    assert scans[2]["scan_number"] == 2253

    response = client.get(
        "/api/v1/scans/session", params={"session_id": session_id, "sort": '{"scan_number": -1}'}
    )

    assert response.status_code == 200
    scans = response.json()
    assert len(scans) == 3
    assert scans[0]["scan_number"] == 2253
    assert scans[1]["scan_number"] == 2252
    assert scans[2]["scan_number"] == 2251


@pytest.mark.timeout(60)
def test_get_scans_for_session_with_invalid_sort(logged_in_client):
    """
    Test that the scans/session endpoint returns 400 for an invalid sort order.
    """
    client = logged_in_client

    session_id = _get_session(client)

    response = client.get(
        "/api/v1/scans/session", params={"session_id": session_id, "sort": "invalid"}
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid sort order. Must be a JSON object with valid keys."
    }


@pytest.mark.timeout(60)
@pytest.mark.parametrize(
    "fields", ["invalid", "{'scan_number': 2251}", 123, [123], ["scan_number", 123]]
)
def test_get_scans_for_session_with_invalid_fields(logged_in_client, fields):
    """
    Test that the scans/sessions endpoint returns 400 for invalid fields.
    """
    client = logged_in_client

    session_id = _get_session(client)

    response = client.get(
        "/api/v1/scans/session", params={"session_id": session_id, "fields": fields}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid fields. Must be a list of valid fields."}


@pytest.mark.timeout(60)
@pytest.mark.parametrize(
    "filter", ["invalid", 123, [123], '{"scan_number": 2251', '{"scan_number": 2251}}']
)
def test_get_scans_for_session_with_invalid_filter(logged_in_client, filter):
    """
    Test that the scans/sessions endpoint returns 400 for invalid filter.
    """
    client = logged_in_client

    session_id = _get_session(client)

    response = client.get(
        "/api/v1/scans/session", params={"session_id": session_id, "filter": filter}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid filter. Must be a JSON object."}


@pytest.mark.timeout(60)
@pytest.mark.parametrize(
    "sort", ["invalid", 123, [123], '{"scan_number": 1', '{"scan_number": 1}}', '{"invalid": 1}']
)
def test_get_scans_for_session_with_invalid_sort_key(logged_in_client, sort):
    """
    Test that the scans/sessions endpoint returns 400 for invalid sort key.
    """
    client = logged_in_client

    session_id = _get_session(client)

    response = client.get("/api/v1/scans/session", params={"session_id": session_id, "sort": sort})

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid sort order. Must be a JSON object with valid keys."
    }


@pytest.mark.timeout(60)
def test_get_scan_with_id(logged_in_client):
    """
    Test that scans/id endpoint returns the correct scan.
    """
    client = logged_in_client

    session_id = _get_session(client)

    response = client.get("/api/v1/scans/session", params={"session_id": session_id})
    assert response.status_code == 200
    scan_id = response.json()[0]["scan_id"]

    response = client.get("/api/v1/scans/id", params={"scan_id": scan_id})
    assert response.status_code == 200
    scan = response.json()
    assert scan["scan_id"] == scan_id


@pytest.mark.timeout(60)
def test_get_scan_with_id_wrong_id(logged_in_client):
    """
    Test that the scans/id endpoint returns a 404 for a wrong scan id.
    """
    client = logged_in_client

    response = client.get("/api/v1/scans/id", params={"scan_id": "wrong_id"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Scan not found"}


@pytest.mark.timeout(60)
def test_get_scan_with_id_and_fields(logged_in_client):
    """
    Test that the scans/id endpoint returns the correct fields.
    """
    client = logged_in_client

    session_id = _get_session(client)

    response = client.get("/api/v1/scans/session", params={"session_id": session_id})
    assert response.status_code == 200
    scan_id = response.json()[0]["scan_id"]

    response = client.get(
        "/api/v1/scans/id", params={"scan_id": scan_id, "fields": ["scan_number"]}
    )
    assert response.status_code == 200
    scan = response.json()
    assert "scan_number" in scan
    assert "dataset_number" not in scan


@pytest.mark.timeout(60)
def test_update_scan_user_data(logged_in_client):
    """
    Test that the scans/id endpoint updates the user_data.
    """
    client = logged_in_client

    session_id = _get_session(client)

    response = client.get("/api/v1/scans/session", params={"session_id": session_id})
    assert response.status_code == 200
    scan_id = response.json()[0]["scan_id"]

    response = client.get("/api/v1/scans/id", params={"scan_id": scan_id})
    assert response.status_code == 200
    scan = response.json()
    assert "scan_data" not in scan

    response = client.patch(
        "/api/v1/scans/user_data",
        params={"scan_id": scan_id},
        json={"name": "test", "user_rating": 5},
    )
    assert response.status_code == 200

    response = client.get("/api/v1/scans/id", params={"scan_id": scan_id})
    assert response.status_code == 200
    scan = response.json()
    assert scan["user_data"] == {"name": "test", "user_rating": 5}


@pytest.mark.timeout(60)
def test_update_scan_user_data_wrong_id(logged_in_client):
    """
    Test that the scans/id endpoint returns 404 for a wrong scan id.
    """
    client = logged_in_client

    response = client.patch(
        "/api/v1/scans/user_data",
        params={"scan_id": "wrong_id"},
        json={"name": "test", "user_rating": 5},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Scan not found"}


@pytest.mark.timeout(60)
@pytest.mark.parametrize(
    "filter, count", [({}, 4), ('{"scan_number": 2251}', 1), ('{"scan_number": 2}', 0)]
)
def test_count_scans(logged_in_client, filter, count):
    """
    Test that the scans/count endpoint returns the correct number of scans.
    """
    client = logged_in_client

    response = client.get("/api/v1/scans/count", params={"filter": filter})
    assert response.status_code == 200
    assert response.json() == {"count": count}


@pytest.mark.timeout(60)
def test_count_scans_with_invalid_filter(logged_in_client):
    """
    Test that the scans/count endpoint returns 400 for an invalid filter.
    """
    client = logged_in_client

    response = client.get("/api/v1/scans/count", params={"filter": "invalid"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid filter. Must be a JSON object."}


@pytest.mark.timeout(60)
def test_count_scans_with_no_results(logged_in_client):
    """
    Test that the scans/count endpoint returns 0 for no results.
    """
    client = logged_in_client

    _filter = {"session_id": str(ObjectId())}
    response = client.get("/api/v1/scans/count", params={"filter": json.dumps(_filter)})
    assert response.status_code == 200
    assert response.json() == {"count": 0}
