import json

import pytest
from bson import ObjectId

from bec_atlas.model.model import MergedMessagingServiceInfo


@pytest.mark.timeout(60)
def test_available_messaging_services(logged_in_client):
    """
    Test that a GET request to the /messagingServices endpoint returns the available messaging services.
    """
    client = logged_in_client
    response = client.get("/api/v1/messagingServices")
    assert response.status_code == 200
    services = response.json()
    assert len(services) == 2


@pytest.mark.timeout(60)
def test_create_messaging_service(logged_in_client, backend):
    """
    Test creating a new messaging service for a session.
    """
    client = logged_in_client
    _, app = backend

    # Get a session to use as parent
    sessions = client.get(
        "/api/v1/sessions", params={"deployment_id": "678aa8d4875568640bd92176"}
    ).json()
    assert len(sessions) > 0
    session_id = sessions[0]["_id"]

    # Create a new messaging service
    new_service = {
        "service_type": "signal",
        "scope": "test_scope",
        "enabled": True,
        "group_id": "test_group",
        "group_link": "https://test.link",
        "parent_id": session_id,
    }

    response = client.post("/api/v1/messagingServices", json=new_service)
    assert response.status_code == 200
    created_service = response.json()
    assert created_service["scope"] == "test_scope"
    assert created_service["service_type"] == "signal"
    assert created_service["parent_id"] == session_id
    assert "_id" in created_service

    # Verify that the created service is added to the database
    db_result = app.datasources.mongodb.find_one(
        collection="messaging_services",
        query_filter={"_id": ObjectId(created_service["_id"])},
        dtype=MergedMessagingServiceInfo,
    )
    assert db_result.id == ObjectId(created_service["_id"])
    assert db_result.scope == "test_scope"
    assert db_result.service_type == "signal"
    assert db_result.parent_id == ObjectId(session_id)


@pytest.mark.timeout(60)
def test_create_messaging_service_without_parent_id(logged_in_client):
    """
    Test that creating a messaging service without parent_id returns 400.
    """
    client = logged_in_client

    new_service = {"service_type": "signal", "scope": "test_scope", "enabled": True}

    response = client.post("/api/v1/messagingServices", json=new_service)
    assert response.status_code == 400
    assert "Parent ID must be provided" in response.json()["detail"]


@pytest.mark.timeout(60)
def test_create_messaging_service_invalid_parent(logged_in_client):
    """
    Test that creating a messaging service with invalid parent_id returns 404.
    """
    client = logged_in_client

    new_service = {
        "service_type": "signal",
        "scope": "test_scope",
        "enabled": True,
        "parent_id": "000000000000000000000000",  # Non-existent ID
    }

    response = client.post("/api/v1/messagingServices", json=new_service)
    assert response.status_code == 404
    assert "Neither session nor deployment found" in response.json()["detail"]


@pytest.mark.timeout(60)
def test_update_messaging_service(logged_in_client):
    """
    Test updating an existing messaging service.
    """
    client = logged_in_client

    # Get existing messaging services
    response = client.get("/api/v1/messagingServices")
    assert response.status_code == 200
    services = response.json()
    assert len(services) > 0

    service_id = services[0]["_id"]

    # Update the service
    update_data = {"scope": "updated_scope", "enabled": False, "group_id": "updated_group"}

    response = client.patch(f"/api/v1/messagingServices/{service_id}", json=update_data)
    assert response.status_code == 200
    updated_service = response.json()
    assert updated_service["scope"] == "updated_scope"
    assert updated_service["enabled"] is False
    assert updated_service["group_id"] == "updated_group"

    # Verify the update persisted
    response = client.get("/api/v1/messagingServices")
    services = response.json()
    updated_service = next(s for s in services if s["_id"] == service_id)
    assert updated_service["scope"] == "updated_scope"


@pytest.mark.timeout(60)
def test_update_messaging_service_invalid_id(logged_in_client):
    """
    Test that updating a messaging service with invalid ID returns 400.
    """
    client = logged_in_client

    update_data = {"scope": "updated_scope"}

    response = client.patch("/api/v1/messagingServices/invalid_id", json=update_data)
    assert response.status_code == 400
    assert "Invalid messaging service id" in response.json()["detail"]


@pytest.mark.timeout(60)
def test_update_messaging_service_not_found(logged_in_client):
    """
    Test that updating a non-existent messaging service returns 404.
    """
    client = logged_in_client

    update_data = {"scope": "updated_scope"}
    non_existent_id = "000000000000000000000000"

    response = client.patch(f"/api/v1/messagingServices/{non_existent_id}", json=update_data)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.timeout(60)
def test_update_messaging_service_no_fields(logged_in_client):
    """
    Test that updating a messaging service with no valid fields returns 400.
    """
    client = logged_in_client

    # Get existing messaging services
    response = client.get("/api/v1/messagingServices")
    services = response.json()
    service_id = services[0]["_id"]

    # Try to update with protected fields only
    update_data = {"parent_id": "some_id", "owner_groups": ["test"], "access_groups": ["test"]}

    response = client.patch(f"/api/v1/messagingServices/{service_id}", json=update_data)
    assert response.status_code == 400
    assert "No valid fields to update" in response.json()["detail"]


@pytest.mark.timeout(60)
def test_delete_messaging_service(logged_in_client):
    """
    Test deleting a messaging service.
    """
    client = logged_in_client

    # Get existing messaging services
    response = client.get("/api/v1/messagingServices")
    services_before = response.json()
    initial_count = len(services_before)
    assert initial_count > 0

    service_id = services_before[0]["_id"]

    # Delete the service
    response = client.delete(f"/api/v1/messagingServices/{service_id}")
    assert response.status_code == 200

    # Verify it's deleted
    response = client.get("/api/v1/messagingServices")
    services_after = response.json()
    assert len(services_after) == initial_count - 1

    # Verify the specific service is gone
    remaining_ids = [s["_id"] for s in services_after]
    assert service_id not in remaining_ids


@pytest.mark.timeout(60)
def test_delete_messaging_service_invalid_id(logged_in_client):
    """
    Test that deleting a messaging service with invalid ID returns 400.
    """
    client = logged_in_client

    response = client.delete("/api/v1/messagingServices/invalid_id")
    assert response.status_code == 400
    assert "Invalid messaging service id" in response.json()["detail"]


@pytest.mark.timeout(60)
def test_delete_messaging_service_not_found(logged_in_client):
    """
    Test that deleting a non-existent messaging service returns 404.
    """
    client = logged_in_client

    non_existent_id = "000000000000000000000000"

    response = client.delete(f"/api/v1/messagingServices/{non_existent_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.timeout(60)
def test_filter_messaging_services(logged_in_client):
    """
    Test filtering messaging services by parent_id.
    """
    client = logged_in_client

    # Get all services first
    response = client.get("/api/v1/messagingServices")
    all_services = response.json()

    if len(all_services) > 0:
        parent_id = all_services[0]["parent_id"]

        # Filter by parent_id
        filter_json = json.dumps({"parent_id": parent_id})
        response = client.get("/api/v1/messagingServices", params={"filter": filter_json})
        assert response.status_code == 200
        filtered_services = response.json()

        # All returned services should have the same parent_id
        for service in filtered_services:
            assert service["parent_id"] == parent_id


@pytest.mark.timeout(60)
def test_update_partial_fields(logged_in_client):
    """
    Test that partial updates work correctly (only specified fields are updated).
    """
    client = logged_in_client

    # Get existing messaging service
    response = client.get("/api/v1/messagingServices")
    services = response.json()
    original_service = services[0]
    service_id = original_service["_id"]
    original_group_id = original_service.get("group_id")

    # Update only the scope field
    update_data = {"scope": "partially_updated_scope"}

    response = client.patch(f"/api/v1/messagingServices/{service_id}", json=update_data)
    assert response.status_code == 200
    updated_service = response.json()

    # Verify only scope changed
    assert updated_service["scope"] == "partially_updated_scope"
    assert updated_service.get("group_id") == original_group_id  # Should remain unchanged
