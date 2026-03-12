import pytest
from bson import ObjectId

from bec_atlas.model.model import Deployments, Experiment, Session


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


@pytest.mark.timeout(60)
def test_get_deployment_by_realm_with_sessions(logged_in_client, backend):
    """
    Test getting deployments with include_session parameter.
    """
    client, app = backend
    db = app.datasources.mongodb

    # Get the existing deployment
    response = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1", "include_session": False}
    )
    assert response.status_code == 200
    deployments = response.json()
    assert len(deployments) == 1
    deployment = deployments[0]
    deployment_id = deployment["_id"]

    # Verify active_session is not included or is null when not requested
    assert "active_session" not in deployment or deployment.get("active_session") is None

    # Create a test session for this deployment
    test_session = Session(
        deployment_id=deployment_id, name="test_session", owner_groups=["admin"], access_groups=[]
    )
    session_result = db.db["sessions"].insert_one(
        test_session.model_dump(by_alias=True, exclude={"id"})
    )
    test_session_id = session_result.inserted_id

    try:
        # Update the deployment to have this session as active_session_id
        db.db["deployments"].update_one(
            {"_id": ObjectId(deployment_id)}, {"$set": {"active_session_id": test_session_id}}
        )

        # Now get deployment with session resolution
        response = client.get(
            "/api/v1/deployments/realm",
            params={"realm": "demo_beamline_1", "include_session": True},
        )
        assert response.status_code == 200
        deployments = response.json()
        assert len(deployments) == 1
        deployment = deployments[0]

        # Verify active_session is populated correctly
        assert "active_session" in deployment
        assert deployment["active_session"] is not None
        assert deployment["active_session"]["_id"] == str(test_session_id)
        assert deployment["active_session"]["name"] == "test_session"
        assert deployment["active_session"]["deployment_id"] == deployment_id
    finally:
        # Clean up
        db.db["sessions"].delete_one({"_id": test_session_id})
        db.db["deployments"].update_one(
            {"_id": ObjectId(deployment_id)}, {"$set": {"active_session_id": None}}
        )


@pytest.mark.timeout(60)
def test_get_deployment_by_id_with_session(logged_in_client, backend):
    """
    Test getting a single deployment with include_session parameter.
    """
    client, app = backend
    db = app.datasources.mongodb

    # Get the deployment first
    deployments = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    # Get deployment without session
    response = client.get(
        "/api/v1/deployments/id", params={"deployment_id": deployment_id, "include_session": False}
    )
    assert response.status_code == 200
    deployment = response.json()
    assert deployment["_id"] == deployment_id
    # Verify active_session is not included or is null
    assert "active_session" not in deployment or deployment.get("active_session") is None

    # Create a test session for this deployment
    test_session = Session(
        deployment_id=deployment_id,
        name="test_session_by_id",
        owner_groups=["admin"],
        access_groups=[],
    )
    session_result = db.db["sessions"].insert_one(
        test_session.model_dump(by_alias=True, exclude={"id"})
    )
    test_session_id = session_result.inserted_id

    try:
        # Update the deployment to have this session as active_session_id
        db.db["deployments"].update_one(
            {"_id": ObjectId(deployment_id)}, {"$set": {"active_session_id": test_session_id}}
        )

        # Get deployment with session resolution
        response = client.get(
            "/api/v1/deployments/id",
            params={"deployment_id": deployment_id, "include_session": True},
        )
        assert response.status_code == 200
        deployment = response.json()
        assert deployment["_id"] == deployment_id

        # Verify active_session is populated correctly
        assert "active_session" in deployment
        assert deployment["active_session"] is not None
        assert deployment["active_session"]["_id"] == str(test_session_id)
        assert deployment["active_session"]["name"] == "test_session_by_id"
        assert deployment["active_session"]["deployment_id"] == deployment_id
    finally:
        # Clean up
        db.db["sessions"].delete_one({"_id": test_session_id})
        db.db["deployments"].update_one(
            {"_id": ObjectId(deployment_id)}, {"$set": {"active_session_id": None}}
        )


@pytest.mark.timeout(60)
def test_get_deployment_with_session_no_active_session(logged_in_client, backend):
    """
    Test that deployments without an active_session_id handle include_session gracefully.
    """
    client, app = backend
    db = app.datasources.mongodb

    # Create a test deployment without active_session_id
    test_deployment = Deployments(
        realm_id="test_realm",
        name="test_deployment_no_session",
        owner_groups=["admin"],
        access_groups=[],
    )
    result = db.db["deployments"].insert_one(
        test_deployment.model_dump(by_alias=True, exclude={"id"})
    )
    test_deployment_id = str(result.inserted_id)

    try:
        # Get deployment with include_session=True
        response = client.get(
            "/api/v1/deployments/id",
            params={"deployment_id": test_deployment_id, "include_session": True},
        )
        assert response.status_code == 200
        deployment = response.json()
        assert deployment["_id"] == test_deployment_id
        # Should not have active_session or it should be null/empty
        assert deployment.get("active_session") is None or deployment.get("active_session") == {}
    finally:
        # Clean up
        db.db["deployments"].delete_one({"_id": ObjectId(test_deployment_id)})


@pytest.mark.timeout(60)
def test_deployments_set_experiment_creates_new_session(logged_in_client, backend):
    """
    Test setting an experiment for a deployment when no session exists.
    Should create a new session and set it as active.
    """

    client, app = backend
    db = app.datasources.mongodb

    # Get the existing deployment
    deployments = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    # Create a test experiment
    experiment_id = "p20240001"
    test_experiment = Experiment(
        id=experiment_id,  # type: ignore
        realm_id="demo_beamline_1",
        proposal="20240001",
        title="Test Experiment",
        firstname="John",
        lastname="Doe",
        email="john.doe@example.com",
        account="jdoe",
        pi_firstname="Jane",
        pi_lastname="Smith",
        pi_email="jane.smith@example.com",
        pi_account="jsmith",
        eaccount="e20240001",
        pgroup="p20240001",
        abstract="Test abstract",
        owner_groups=["admin"],
        access_groups=["p20240001"],
    )
    db.db["experiments"].insert_one(test_experiment.model_dump(by_alias=True))

    try:
        # Set the experiment for the deployment
        response = client.post(
            "/api/v1/deployments/experiment",
            params={"experiment_id": experiment_id, "deployment_id": deployment_id},
        )
        assert response.status_code == 200
        deployment = response.json()

        # Verify the deployment has an active session
        assert "active_session" in deployment
        assert deployment["active_session"] is not None
        active_session = deployment["active_session"]
        assert active_session["experiment_id"] == experiment_id
        assert active_session["deployment_id"] == deployment_id
        assert active_session["name"] == experiment_id
        assert "p20240001" in active_session["access_groups"]

        # Verify the experiment is nested within the active_session
        assert "experiment" in active_session, "Experiment should be included in active_session"
        assert active_session["experiment"] is not None, "Experiment should not be None"
        experiment = active_session["experiment"]
        assert experiment["_id"] == experiment_id
        assert experiment["proposal"] == "20240001"
        assert experiment["title"] == "Test Experiment"
        assert experiment["firstname"] == "John"
        assert experiment["lastname"] == "Doe"
        assert experiment["realm_id"] == "demo_beamline_1"

        # Verify the session was created in the database
        session_id = active_session["_id"]
        created_session = db.db["sessions"].find_one({"_id": ObjectId(session_id)})
        assert created_session is not None
        assert created_session["experiment_id"] == experiment_id
        assert str(created_session["deployment_id"]) == deployment_id

    finally:
        # Clean up
        db.db["experiments"].delete_one({"_id": experiment_id})
        if "session_id" in locals():
            db.db["sessions"].delete_one({"_id": ObjectId(session_id)})
        db.db["deployments"].update_one(
            {"_id": ObjectId(deployment_id)}, {"$set": {"active_session_id": None}}
        )


@pytest.mark.timeout(60)
def test_deployments_set_experiment_reuses_existing_session(logged_in_client, backend):
    """
    Test setting an experiment for a deployment when a session already exists.
    Should reuse the existing session instead of creating a new one.
    """

    client, app = backend
    db = app.datasources.mongodb

    # Get the existing deployment
    deployments = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    # Create a test experiment
    experiment_id = "p20240002"
    test_experiment = Experiment(
        id=experiment_id,  # type: ignore
        realm_id="demo_beamline_1",
        proposal="20240002",
        title="Test Experiment 2",
        firstname="Alice",
        lastname="Johnson",
        email="alice.johnson@example.com",
        account="ajohnson",
        pi_firstname="Bob",
        pi_lastname="Wilson",
        pi_email="bob.wilson@example.com",
        pi_account="bwilson",
        eaccount="e20240002",
        pgroup="p20240002",
        abstract="Another test abstract",
        owner_groups=["admin"],
        access_groups=["p20240002"],
    )
    db.db["experiments"].insert_one(test_experiment.model_dump(by_alias=True))

    # Create a session for this experiment and deployment
    existing_session = Session(
        deployment_id=deployment_id,
        experiment_id=experiment_id,
        name="existing_test_session",
        owner_groups=["admin"],
        access_groups=["p20240002"],
    )
    session_result = db.db["sessions"].insert_one(
        existing_session.model_dump(by_alias=True, exclude={"id"})
    )
    existing_session_id = str(session_result.inserted_id)

    try:
        # Set the experiment for the deployment
        response = client.post(
            "/api/v1/deployments/experiment",
            params={"experiment_id": experiment_id, "deployment_id": deployment_id},
        )
        assert response.status_code == 200
        deployment = response.json()

        # Verify the deployment uses the existing session
        assert "active_session" in deployment
        assert deployment["active_session"] is not None
        active_session = deployment["active_session"]
        assert active_session["_id"] == existing_session_id
        assert active_session["name"] == "existing_test_session"
        assert active_session["experiment_id"] == experiment_id

        # Verify the experiment is nested within the active_session
        assert "experiment" in active_session, "Experiment should be included in active_session"
        assert active_session["experiment"] is not None, "Experiment should not be None"
        experiment = active_session["experiment"]
        assert experiment["_id"] == experiment_id
        assert experiment["proposal"] == "20240002"
        assert experiment["title"] == "Test Experiment 2"
        assert experiment["firstname"] == "Alice"
        assert experiment["lastname"] == "Johnson"
        assert experiment["realm_id"] == "demo_beamline_1"

        # Verify no new session was created
        session_count = db.db["sessions"].count_documents(
            {"experiment_id": experiment_id, "deployment_id": ObjectId(deployment_id)}
        )
        assert session_count == 1  # Only the existing session

    finally:
        # Clean up
        db.db["experiments"].delete_one({"_id": experiment_id})
        db.db["sessions"].delete_one({"_id": ObjectId(existing_session_id)})
        db.db["deployments"].update_one(
            {"_id": ObjectId(deployment_id)}, {"$set": {"active_session_id": None}}
        )


@pytest.mark.timeout(60)
def test_deployments_set_experiment_already_active(logged_in_client, backend):
    """
    Test setting an experiment that is already active on the deployment.
    Should return early without modifying anything.
    """

    client, app = backend
    db = app.datasources.mongodb

    # Get the existing deployment
    deployments = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    # Create a test experiment
    experiment_id = "p20240003"
    test_experiment = Experiment(
        id=experiment_id,  # type: ignore
        realm_id="demo_beamline_1",
        proposal="20240003",
        title="Test Experiment 3",
        firstname="Charlie",
        lastname="Brown",
        email="charlie.brown@example.com",
        account="cbrown",
        pi_firstname="David",
        pi_lastname="Green",
        pi_email="david.green@example.com",
        pi_account="dgreen",
        eaccount="e20240003",
        pgroup="p20240003",
        abstract="Yet another test abstract",
        owner_groups=["admin"],
        access_groups=["p20240003"],
    )
    db.db["experiments"].insert_one(test_experiment.model_dump(by_alias=True))

    # Create a session with this experiment
    test_session = Session(
        deployment_id=deployment_id,
        experiment_id=experiment_id,
        name="active_session",
        owner_groups=["admin"],
        access_groups=["p20240003"],
    )
    session_result = db.db["sessions"].insert_one(
        test_session.model_dump(by_alias=True, exclude={"id"})
    )
    test_session_id = session_result.inserted_id

    # Set this session as active on the deployment
    db.db["deployments"].update_one(
        {"_id": ObjectId(deployment_id)}, {"$set": {"active_session_id": test_session_id}}
    )

    try:
        # Try to set the same experiment again
        response = client.post(
            "/api/v1/deployments/experiment",
            params={"experiment_id": experiment_id, "deployment_id": deployment_id},
        )
        assert response.status_code == 200
        deployment = response.json()

        # Verify the deployment still has the same active session
        assert "active_session" in deployment
        assert deployment["active_session"] is not None
        active_session = deployment["active_session"]
        assert active_session["_id"] == str(test_session_id)
        assert active_session["experiment_id"] == experiment_id

        # Verify no new session was created
        session_count = db.db["sessions"].count_documents(
            {"experiment_id": experiment_id, "deployment_id": ObjectId(deployment_id)}
        )
        assert session_count == 1  # Only the original session

    finally:
        # Clean up
        db.db["experiments"].delete_one({"_id": experiment_id})
        db.db["sessions"].delete_one({"_id": test_session_id})
        db.db["deployments"].update_one(
            {"_id": ObjectId(deployment_id)}, {"$set": {"active_session_id": None}}
        )


@pytest.mark.timeout(60)
def test_deployments_set_experiment_invalid_deployment_id(logged_in_client):
    """
    Test setting an experiment with an invalid deployment_id.
    Should return a 400 error.
    """
    client = logged_in_client

    response = client.post(
        "/api/v1/deployments/experiment",
        params={"experiment_id": "some_experiment_id", "deployment_id": "invalid_id"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid deployment id"}


@pytest.mark.timeout(60)
def test_deployments_set_experiment_deployment_not_found(logged_in_client):
    """
    Test setting an experiment for a non-existent deployment.
    Should return a 404 error.
    """
    client = logged_in_client

    # Use a valid ObjectId format but one that doesn't exist
    non_existent_deployment_id = str(ObjectId())

    response = client.post(
        "/api/v1/deployments/experiment",
        params={"experiment_id": "some_experiment_id", "deployment_id": non_existent_deployment_id},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Deployment not found"}


@pytest.mark.timeout(60)
def test_deployments_set_experiment_experiment_not_found(logged_in_client, backend):
    """
    Test setting a non-existent experiment for a deployment.
    Should return a 404 error.
    """
    client, app = backend

    # Get the existing deployment
    deployments = client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    # Use a valid ObjectId format but one that doesn't exist
    non_existent_experiment_id = str(ObjectId())

    response = client.post(
        "/api/v1/deployments/experiment",
        params={"experiment_id": non_existent_experiment_id, "deployment_id": deployment_id},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Experiment not found"}


@pytest.mark.timeout(60)
def test_get_full_deployment_includes_experiment(logged_in_client, backend):
    """
    Test that get_full_deployment includes the experiment nested within the active_session.

    This is a regression test for the bug where 'experiment' was missing from the
    active_session include in get_full_deployment, causing it to always be None.
    """
    client, app = backend
    db = app.datasources.mongodb

    # Get the existing deployment
    deployments = logged_in_client.get(
        "/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}
    ).json()
    deployment_id = deployments[0]["_id"]

    # Create a test experiment
    experiment_id = "p20240010"
    test_experiment = Experiment(
        id=experiment_id,  # type: ignore
        realm_id="demo_beamline_1",
        proposal="20240010",
        title="Full Deployment Test Experiment",
        firstname="Test",
        lastname="User",
        email="test.user@example.com",
        account="tuser",
        pi_firstname="PI",
        pi_lastname="User",
        pi_email="pi.user@example.com",
        pi_account="piuser",
        eaccount="e20240010",
        pgroup="p20240010",
        abstract="Regression test abstract",
        owner_groups=["admin"],
        access_groups=["p20240010"],
    )
    db.db["experiments"].insert_one(test_experiment.model_dump(by_alias=True))

    # Create a session linked to the experiment
    test_session = Session(
        deployment_id=deployment_id,
        experiment_id=experiment_id,
        name="full_deployment_test_session",
        owner_groups=["admin"],
        access_groups=["p20240010"],
    )
    session_result = db.db["sessions"].insert_one(
        test_session.model_dump(by_alias=True, exclude={"id"})
    )
    test_session_id = session_result.inserted_id

    # Set the session as active on the deployment
    db.db["deployments"].update_one(
        {"_id": ObjectId(deployment_id)}, {"$set": {"active_session_id": test_session_id}}
    )

    try:
        result = db.get_full_deployment({"_id": deployment_id})
        assert len(result) == 1
        deployment = result[0]

        # Verify active_session is populated
        assert deployment.active_session is not None
        active_session = deployment.active_session

        # Verify the experiment is nested within active_session
        assert active_session.experiment is not None, (
            "Experiment should be included in active_session (regression test for missing "
            "'experiment' in get_full_deployment include)"
        )
        assert active_session.experiment.id == experiment_id
        assert active_session.experiment.proposal == "20240010"
        assert active_session.experiment.title == "Full Deployment Test Experiment"
        assert active_session.experiment.realm_id == "demo_beamline_1"
    finally:
        db.db["experiments"].delete_one({"_id": experiment_id})
        db.db["sessions"].delete_one({"_id": test_session_id})
        db.db["deployments"].update_one(
            {"_id": ObjectId(deployment_id)}, {"$set": {"active_session_id": None}}
        )
