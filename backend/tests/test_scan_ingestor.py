from typing import TYPE_CHECKING
from unittest import mock

import pytest
from bec_lib import messages
from bson import ObjectId

from bec_atlas.ingestor.data_ingestor import DataIngestor
from bec_atlas.model.model import Deployments, Experiment, Session

if TYPE_CHECKING:
    from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource


@pytest.fixture
def scan_ingestor(backend):
    client, app = backend
    app.redis_websocket.users = {}
    ingestor = DataIngestor(config=app.config)
    yield ingestor
    ingestor.shutdown()


@pytest.mark.timeout(60)
def test_scan_ingestor_create_scan(scan_ingestor, backend):
    """
    Test that the login endpoint returns a token.
    """
    client, app = backend
    mongo: MongoDBDatasource = app.datasources.mongodb
    deployment_id = str(mongo.find_one("deployments", {}, dtype=Deployments).id)
    session_id = str(mongo.find_one("sessions", {"deployment_id": deployment_id}, dtype=Session).id)
    msg = messages.ScanStatusMessage(
        metadata={},
        scan_id="92429a81-4bd4-41c2-82df-eccfaddf3d96",
        status="open",
        # session_id="5cc67967-744d-4115-a46b-13246580cb3f",
        info={
            "readout_priority": {
                "monitored": ["bpm3i", "diode", "ftp", "bpm5c", "bpm3x", "bpm3z", "bpm4x"],
                "baseline": ["ddg1a", "bs1y", "mobdco"],
                "async": ["eiger", "monitor_async", "waveform"],
                "continuous": [],
                "on_request": ["flyer_sim"],
            },
            "file_suffix": None,
            "file_directory": None,
            "user_metadata": {"sample_name": "testA"},
            "RID": "5cc67967-744d-4115-a46b-13246580cb3f",
            "scan_id": "92429a81-4bd4-41c2-82df-eccfaddf3d96",
            "queue_id": "7d77d976-bee0-4bb8-aabb-2b862b4506ec",
            "session_id": session_id,
            "scan_motors": ["samx"],
            "num_points": 10,
            "positions": [
                [-5.0024118137239455],
                [-3.8913007026128343],
                [-2.780189591501723],
                [-1.6690784803906122],
                [-0.557967369279501],
                [0.5531437418316097],
                [1.6642548529427212],
                [2.775365964053833],
                [3.886477075164944],
                [4.9975881862760545],
            ],
            "scan_name": "line_scan",
            "scan_type": "step",
            "scan_number": 2,
            "dataset_number": 2,
            "exp_time": 0,
            "frames_per_trigger": 1,
            "settling_time": 0,
            "readout_time": 0,
            "acquisition_config": {"default": {"exp_time": 0, "readout_time": 0}},
            "scan_report_devices": ["samx"],
            "monitor_sync": "bec",
            "scan_msgs": [
                "metadata={'file_suffix': None, 'file_directory': None, 'user_metadata': {'sample_name': 'testA'}, 'RID': '5cc67967-744d-4115-a46b-13246580cb3f'} scan_type='line_scan' parameter={'args': {'samx': [-5, 5]}, 'kwargs': {'steps': 10, 'exp_time': 0, 'relative': True, 'system_config': {'file_suffix': None, 'file_directory': None}}} queue='primary'"
            ],
            "args": {"samx": [-5, 5]},
            "kwargs": {
                "steps": 10,
                "exp_time": 0,
                "relative": True,
                "system_config": {"file_suffix": None, "file_directory": None},
            },
        },
        timestamp=1732610545.15924,
    )
    scan_ingestor.update_scan_status(msg, deployment_id=deployment_id)

    response = client.post(
        "/api/v1/user/login", json={"username": "admin@bec_atlas.ch", "password": "admin"}
    )

    session_id = msg.info.get("session_id")
    scan_id = msg.scan_id
    response = client.get("/api/v1/scans/session", params={"session_id": session_id})
    assert response.status_code == 200
    out = response.json()
    num_scans = len(out)
    inserted_scan = [scan for scan in out if scan["scan_id"] == scan_id]

    assert len(inserted_scan) == 1
    out = inserted_scan[0]
    # assert out["session_id"] == session_id
    assert out["scan_id"] == scan_id
    assert out["status"] == "open"

    msg.status = "closed"
    scan_ingestor.update_scan_status(msg, deployment_id=deployment_id)
    response = client.get("/api/v1/scans/id", params={"scan_id": scan_id})
    assert response.status_code == 200
    out = response.json()
    assert out["status"] == "closed"
    assert out["scan_id"] == scan_id

    # Test that the number of scans did not change
    response = client.get("/api/v1/scans/session", params={"session_id": session_id})
    assert response.status_code == 200
    out = response.json()
    assert len(out) == num_scans


@pytest.mark.timeout(60)
def test_scan_ingestor_scan_history(scan_ingestor, backend):
    """
    Test that the scan history ingestion works correctly.
    """
    client, app = backend
    mongo: MongoDBDatasource = app.datasources.mongodb
    deployment = mongo.find_one("deployments", {}, dtype=Deployments)
    assert deployment is not None, "No deployment found in test data"
    deployment_id = str(deployment.id)
    session = mongo.find_one("sessions", {"deployment_id": deployment_id}, dtype=Session)
    assert session is not None, f"No session found for deployment {deployment_id}"
    session_id = str(session.id)

    # First create a scan using scan_status
    scan_id = "test-scan-history-123"
    status_msg = messages.ScanStatusMessage(
        metadata={},
        scan_id=scan_id,
        status="open",
        session_id=session_id,  # Put session_id directly on the message
        info={"scan_name": "test_scan", "scan_number": 1, "dataset_number": 1},
        timestamp=1732610545.15924,
    )
    scan_ingestor.update_scan_status(status_msg, deployment_id=deployment_id)

    # Now update scan history
    history_msg = messages.ScanHistoryMessage(
        scan_id=scan_id,
        scan_number=1,
        dataset_number=1,
        file_path="/path/to/scan/data.h5",
        exit_status="closed",
        start_time=1732610545.0,
        end_time=1732610600.0,
        scan_name="test_scan",
        num_points=100,
        metadata={"test": "metadata"},
    )
    scan_ingestor.update_scan_history(history_msg, deployment_id)

    # Login first before making API calls
    response = client.post(
        "/api/v1/user/login", json={"username": "admin@bec_atlas.ch", "password": "admin"}
    )
    assert response.status_code == 200

    # Verify the scan was updated with history information
    response = client.get("/api/v1/scans/id", params={"scan_id": scan_id})
    assert response.status_code == 200
    out = response.json()
    assert out["scan_id"] == scan_id
    assert out["start_time"] == 1732610545.0
    assert out["end_time"] == 1732610600.0
    assert out["file_path"] == "/path/to/scan/data.h5"


@pytest.mark.timeout(60)
def test_scan_ingestor_account_update(scan_ingestor, backend):
    """
    Test that account updates create/manage experiment sessions correctly.
    """
    client, app = backend
    mongo: MongoDBDatasource = app.datasources.mongodb
    deployment = mongo.find_one("deployments", {}, dtype=Deployments)
    assert deployment is not None, "No deployment found in test data"
    deployment_id = str(deployment.id)

    # Create experiment data with string _id
    experiment_id_string = "test_experiment_id_123"
    experiment_data = {
        "realm_id": "test_realm",
        "proposal": "test_proposal_123",
        "title": "Test Experiment",
        "firstname": "Test",
        "lastname": "User",
        "email": "test@example.com",
        "account": "test_experiment_123",
        "pi_firstname": "PI",
        "pi_lastname": "User",
        "pi_email": "pi@example.com",
        "pi_account": "pi_account",
        "eaccount": "test_eaccount",
        "pgroup": "test_pgroup",
        "abstract": "Test experiment abstract",
        "access_groups": ["test_pgroup"],
        "owner_groups": ["admin"],
        "_id": experiment_id_string,  # Use string _id
    }
    # Ensure that it complies with the model
    Experiment(**experiment_data)

    # Use the ingestor's datasource to insert the experiment
    scan_ingestor.datasource.db["experiments"].insert_one(experiment_data)

    # Create account update message with the string experiment _id
    account_msg = messages.VariableMessage(
        value=experiment_id_string, metadata={}  # This will match the experiment's _id
    )

    # Update account - this should find the experiment and create/use a session for it
    scan_ingestor.update_account(account_msg, deployment_id)

    # Verify experiment exists
    experiments = list(
        mongo.find("experiments", {"account": "test_experiment_123"}, dtype=Experiment)
    )
    assert len(experiments) > 0
    experiment = experiments[0]
    assert experiment.account == "test_experiment_123"
    assert experiment.pgroup == "test_pgroup"

    # Verify deployment's active_session_id was updated
    updated_deployment = mongo.find_one(
        "deployments", {"_id": ObjectId(deployment_id)}, dtype=Deployments
    )
    assert updated_deployment is not None
    assert updated_deployment.active_session_id is not None

    # Verify session exists and is linked to the experiment
    session = mongo.find_one(
        "sessions", {"_id": ObjectId(updated_deployment.active_session_id)}, dtype=Session
    )
    assert session is not None
    assert session.experiment_id == experiment_id_string  # Should be linked to our experiment
    assert session.name == experiment_id_string  # Name should be the experiment_id_string


@pytest.mark.timeout(60)
def test_scan_ingestor_account_update_default_session(scan_ingestor, backend):
    """
    Test that account update with None/empty values switches to default session.
    """
    client, app = backend
    mongo: MongoDBDatasource = app.datasources.mongodb
    deployment = mongo.find_one("deployments", {}, dtype=Deployments)
    assert deployment is not None, "No deployment found in test data"
    deployment_id = str(deployment.id)

    # Find the default session
    default_session = mongo.find_one(
        "sessions", {"name": "_default_", "deployment_id": deployment_id}, dtype=Session
    )
    assert default_session is not None, "No default session found"
    default_session_id = str(default_session.id)

    # Create an account update message with None account
    account_msg = messages.VariableMessage(value={"account": None}, metadata={})

    # Update account
    scan_ingestor.update_account(account_msg, deployment_id)

    # Verify deployment's active_session_id is set to default session
    updated_deployment = mongo.find_one(
        "deployments", {"_id": ObjectId(deployment_id)}, dtype=Deployments
    )
    assert updated_deployment is not None
    assert updated_deployment.active_session_id == default_session_id


@pytest.mark.timeout(60)
def test_scan_ingestor_error_handling(scan_ingestor, backend):
    """
    Test error handling for invalid messages and missing data.
    """
    client, app = backend
    mongo: MongoDBDatasource = app.datasources.mongodb
    deployment = mongo.find_one("deployments", {}, dtype=Deployments)
    assert deployment is not None, "No deployment found in test data"
    deployment_id = str(deployment.id)

    # Test handling of scan status with non-existent session
    msg = messages.ScanStatusMessage(
        metadata={},
        scan_id="test-scan-error",
        status="open",
        session_id="507f1f77bcf86cd799439011",  # Valid ObjectId format that doesn't exist
        info={"scan_name": "test_scan"},
        timestamp=1732610545.0,
    )

    # This should not raise an exception but handle the error gracefully
    scan_ingestor.update_scan_status(msg, deployment_id=deployment_id)

    # Login first before making API calls
    response = client.post(
        "/api/v1/user/login", json={"username": "admin@bec_atlas.ch", "password": "admin"}
    )
    assert response.status_code == 200

    # Verify scan was not created due to invalid session
    response = client.get("/api/v1/scans/id", params={"scan_id": "test-scan-error"})
    assert response.status_code == 404


@pytest.mark.timeout(60)
def test_scan_ingestor_consumer_groups(scan_ingestor, backend):
    """
    Test consumer group management functionality.
    """
    client, app = backend

    # Mock the actual redis connection's xgroup_create method
    with mock.patch.object(scan_ingestor.redis._redis_conn, "xgroup_create") as mock_xgroup_create:
        # Test update_consumer_groups method
        scan_ingestor.update_consumer_groups()
        # Verify consumer groups were created for all deployments
        mock_xgroup_create.assert_called()
        # The exact number of calls depends on deployments in test data
        assert mock_xgroup_create.call_count > 0


@pytest.mark.timeout(60)
def test_set_scilog_logbook_for_session_matching_logbook(scan_ingestor, backend):
    """Test that SciLog messaging service is added when matching logbook exists."""
    client, app = backend
    from bec_lib import messages

    mongo: MongoDBDatasource = app.datasources.mongodb
    deployment = mongo.find_one("deployments", {}, dtype=Deployments)
    deployment_id = str(deployment.id)

    # Create experiment with pgroup
    experiment_id = "exp_scilog_123"
    experiment_data = {
        "_id": experiment_id,
        "pgroup": "test_pgroup_001",
        "access_groups": ["test_pgroup_001"],
        "owner_groups": ["admin"],
    }
    mongo.db["experiments"].insert_one(experiment_data)

    # Create session for this experiment
    session = Session(
        name=experiment_id,
        experiment_id=experiment_id,
        deployment_id=deployment_id,
        owner_groups=["admin"],
        access_groups=["test_pgroup_001"],
    )
    session_id = mongo.db["sessions"].insert_one(session.model_dump())
    session.id = session_id.inserted_id

    # Mock Redis response with available logbooks (ownerGroup must match experiment_id)
    logbooks_msg = messages.AvailableResourceMessage(
        resource=[
            {"id": "lb1", "name": "Logbook 1", "ownerGroup": experiment_id},
            {"id": "lb2", "name": "Logbook 2", "ownerGroup": "other_group"},
        ]
    )
    with mock.patch.object(scan_ingestor.redis, "get", return_value=logbooks_msg):
        scan_ingestor._set_scilog_logbook_for_session(session, deployment.realm_id, experiment_data)

    # Verify messaging service was added
    updated_session = mongo.find_one("sessions", {"_id": session_id.inserted_id}, dtype=Session)
    assert len(updated_session.messaging_services) == 1
    assert updated_session.messaging_services[0].service_name == "scilog"
    assert updated_session.messaging_services[0].scopes == ["lb1"]


@pytest.mark.timeout(60)
def test_set_scilog_logbook_for_session_no_matching_logbook(scan_ingestor, backend):
    """Test that no messaging service is added when no matching logbook exists."""
    client, app = backend
    from bec_lib import messages

    mongo: MongoDBDatasource = app.datasources.mongodb
    deployment = mongo.find_one("deployments", {}, dtype=Deployments)
    deployment_id = str(deployment.id)

    # Create session
    session = Session(
        name="test_session",
        experiment_id="exp_no_match",
        deployment_id=deployment_id,
        owner_groups=["admin"],
        access_groups=["test_group"],
    )
    session_id = mongo.db["sessions"].insert_one(session.model_dump())
    session.id = session_id.inserted_id

    # Mock Redis response with non-matching logbooks
    logbooks_msg = messages.AvailableResourceMessage(
        resource=[{"id": "lb1", "name": "Logbook 1", "ownerGroup": "different_group"}]
    )
    with mock.patch.object(scan_ingestor.redis, "get", return_value=logbooks_msg):
        scan_ingestor._set_scilog_logbook_for_session(session, deployment.realm_id, {})

    # Verify no messaging service was added
    updated_session = mongo.find_one("sessions", {"_id": session_id.inserted_id}, dtype=Session)
    assert len(updated_session.messaging_services) == 0


@pytest.mark.timeout(60)
def test_set_scilog_logbook_for_session_no_logbooks_available(scan_ingestor, backend):
    """Test graceful handling when no logbooks are available."""
    client, app = backend

    mongo: MongoDBDatasource = app.datasources.mongodb
    deployment = mongo.find_one("deployments", {}, dtype=Deployments)
    deployment_id = str(deployment.id)

    # Create session
    session = Session(
        name="test_session",
        experiment_id="exp_no_logbooks",
        deployment_id=deployment_id,
        owner_groups=["admin"],
        access_groups=["test_group"],
    )
    session_id = mongo.db["sessions"].insert_one(session.model_dump())
    session.id = session_id.inserted_id

    # Mock Redis response with None (no logbooks)
    with mock.patch.object(scan_ingestor.redis, "get", return_value=None):
        scan_ingestor._set_scilog_logbook_for_session(session, deployment.realm_id, {})

    # Verify no messaging service was added
    updated_session = mongo.find_one("sessions", {"_id": session_id.inserted_id}, dtype=Session)
    assert len(updated_session.messaging_services) == 0
