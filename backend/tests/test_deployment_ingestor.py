from unittest import mock

import mongomock
import pymongo
import pytest

from bec_atlas.ingestor.deployment_ingestor import DeploymentIngestor


@pytest.fixture
def deployment_ingestor():
    """Create a DeploymentIngestor instance with mock MongoDB."""
    config = {"host": "localhost", "port": 27017}
    ingestor = DeploymentIngestor(config)
    ingestor.client = mongomock.MongoClient("localhost", 27017)
    ingestor.db = ingestor.client["bec_atlas"]
    return ingestor


@pytest.fixture
def sample_deployment_data():
    """Sample deployment data for testing."""
    return {
        "test_realm": {
            "xname": "x99za",
            "managers": ["test_manager_group"],
            "deployments": {
                "test-host-001.psi.ch": {
                    "name": "production",
                    "description": "Primary deployment for test realm",
                    "deployment_access": ["test_deployment_group"],
                    "experiment_access": ["test_experiment_group"],
                },
                "test-host-002.psi.ch": {
                    "name": "test",
                    "description": "Test environment",
                    "deployment_access": ["test_deployment_group"],
                    "experiment_access": ["test_experiment_group"],
                },
            },
        },
        "another_realm": {
            "managers": ["another_manager_group"],
            "deployments": {
                "another-host-001.psi.ch": {
                    "name": "production",
                    "deployment_access": ["another_deployment_group"],
                    "experiment_access": ["another_experiment_group"],
                }
            },
        },
    }


@pytest.mark.timeout(60)
def test_deployment_ingestor_init():
    """Test DeploymentIngestor initialization."""
    config = {"host": "localhost", "port": 27017}
    ingestor = DeploymentIngestor(config)

    assert ingestor.config == config
    assert isinstance(ingestor.client, pymongo.MongoClient)
    assert ingestor.db.name == "bec_atlas"
    assert ingestor._data == {}


@pytest.mark.timeout(60)
def test_load_complete_deployment_data(deployment_ingestor, sample_deployment_data):
    """Test loading complete deployment data."""
    deployment_ingestor.load(sample_deployment_data)

    # Check that realms were created
    realms = list(deployment_ingestor.db["realms"].find())
    assert len(realms) == 2

    realm_ids = {realm["realm_id"] for realm in realms}
    assert "test_realm" in realm_ids
    assert "another_realm" in realm_ids

    # Check realm data
    test_realm = deployment_ingestor.db["realms"].find_one({"realm_id": "test_realm"})
    assert test_realm["name"] == "test_realm"
    assert test_realm["xname"] == "x99za"
    assert test_realm["managers"] == ["test_manager_group"]
    assert test_realm["owner_groups"] == ["admin"]
    assert test_realm["access_groups"] == ["auth_user"]

    # Check deployments were created
    deployments = list(deployment_ingestor.db["deployments"].find())
    assert len(deployments) == 3

    deployment_names = {deployment["name"] for deployment in deployments}
    assert "test-host-001.psi.ch" in deployment_names
    assert "test-host-002.psi.ch" in deployment_names
    assert "another-host-001.psi.ch" in deployment_names


@pytest.mark.timeout(60)
def test_load_realm_creation(deployment_ingestor, sample_deployment_data):
    """Test realm creation during deployment loading."""
    deployment_ingestor.load(sample_deployment_data)

    test_realm = deployment_ingestor.db["realms"].find_one({"realm_id": "test_realm"})
    assert test_realm is not None
    assert test_realm["realm_id"] == "test_realm"
    assert test_realm["name"] == "test_realm"
    assert test_realm["xname"] == "x99za"
    assert test_realm["managers"] == ["test_manager_group"]
    assert test_realm["owner_groups"] == ["admin"]
    assert test_realm["access_groups"] == ["auth_user"]
    assert test_realm["_id"] == "test_realm"


@pytest.mark.timeout(60)
def test_load_realm_without_xname(deployment_ingestor):
    """Test realm creation when xname is not provided."""
    data = {"realm_without_xname": {"managers": ["manager_group"], "deployments": {}}}
    deployment_ingestor.load(data)

    realm = deployment_ingestor.db["realms"].find_one({"realm_id": "realm_without_xname"})
    assert realm is not None
    assert realm["xname"] is None


@pytest.mark.timeout(60)
def test_load_realm_duplicate_prevention(deployment_ingestor, sample_deployment_data):
    """Test that duplicate realms are not created."""
    # Load data first time
    deployment_ingestor.load(sample_deployment_data)
    realms_count_first = deployment_ingestor.db["realms"].count_documents({})

    # Load data second time
    deployment_ingestor.load(sample_deployment_data)
    realms_count_second = deployment_ingestor.db["realms"].count_documents({})

    assert realms_count_first == realms_count_second == 2


@pytest.mark.timeout(60)
def test_load_deployment_creation(deployment_ingestor, sample_deployment_data):
    """Test deployment creation during loading."""
    deployment_ingestor.load(sample_deployment_data)

    deployment = deployment_ingestor.db["deployments"].find_one({"name": "test-host-001.psi.ch"})
    assert deployment is not None
    assert deployment["realm_id"] == "test_realm"
    assert deployment["name"] == "test-host-001.psi.ch"
    assert deployment["owner_groups"] == ["admin"]
    assert deployment["access_groups"] == ["test_deployment_group"]


@pytest.mark.timeout(60)
def test_load_deployment_access_groups_update(deployment_ingestor, sample_deployment_data):
    """Test that deployment access groups are updated when changed."""
    # Load initial data
    deployment_ingestor.load(sample_deployment_data)

    # Modify access groups
    modified_data = sample_deployment_data.copy()
    modified_data["test_realm"]["deployments"]["test-host-001.psi.ch"]["deployment_access"] = [
        "new_group"
    ]

    # Load modified data
    deployment_ingestor.load(modified_data)

    deployment = deployment_ingestor.db["deployments"].find_one({"name": "test-host-001.psi.ch"})
    assert deployment["access_groups"] == ["new_group"]


@pytest.mark.timeout(60)
def test_load_deployment_duplicate_prevention(deployment_ingestor, sample_deployment_data):
    """Test that duplicate deployments are not created."""
    # Load data first time
    deployment_ingestor.load(sample_deployment_data)
    deployments_count_first = deployment_ingestor.db["deployments"].count_documents({})

    # Load data second time
    deployment_ingestor.load(sample_deployment_data)
    deployments_count_second = deployment_ingestor.db["deployments"].count_documents({})

    assert deployments_count_first == deployments_count_second == 3


@pytest.mark.timeout(60)
def test_load_default_session_creation(deployment_ingestor, sample_deployment_data):
    """Test default session creation for deployments."""
    deployment_ingestor.load(sample_deployment_data)

    deployment = deployment_ingestor.db["deployments"].find_one({"name": "test-host-001.psi.ch"})
    session = deployment_ingestor.db["sessions"].find_one(
        {"name": "_default_", "deployment_id": str(deployment["_id"])}
    )

    assert session is not None
    assert session["name"] == "_default_"
    assert session["deployment_id"] == str(deployment["_id"])
    assert session["owner_groups"] == ["test_deployment_group"]
    assert session["access_groups"] == ["test_experiment_group"]


@pytest.mark.timeout(60)
def test_load_default_session_access_groups_update(deployment_ingestor, sample_deployment_data):
    """Test that default session access groups are updated when changed."""
    # Load initial data
    deployment_ingestor.load(sample_deployment_data)

    # Modify experiment access groups
    modified_data = sample_deployment_data.copy()
    modified_data["test_realm"]["deployments"]["test-host-001.psi.ch"]["experiment_access"] = [
        "new_exp_group"
    ]
    modified_data["test_realm"]["deployments"]["test-host-001.psi.ch"]["deployment_access"] = [
        "new_dep_group"
    ]

    # Load modified data
    deployment_ingestor.load(modified_data)

    deployment = deployment_ingestor.db["deployments"].find_one({"name": "test-host-001.psi.ch"})
    session = deployment_ingestor.db["sessions"].find_one(
        {"name": "_default_", "deployment_id": str(deployment["_id"])}
    )

    assert session["access_groups"] == ["new_exp_group"]
    assert session["owner_groups"] == ["new_dep_group"]


@pytest.mark.timeout(60)
def test_load_deployment_credentials_creation(deployment_ingestor, sample_deployment_data):
    """Test deployment credentials creation."""
    deployment_ingestor.load(sample_deployment_data)

    deployment = deployment_ingestor.db["deployments"].find_one({"name": "test-host-001.psi.ch"})
    credentials = deployment_ingestor.db["deployment_credentials"].find_one(
        {"_id": deployment["_id"]}
    )

    assert credentials is not None
    assert credentials["_id"] == deployment["_id"]
    assert "credential" in credentials
    assert len(credentials["credential"]) > 20  # URL-safe tokens are typically longer


@pytest.mark.timeout(60)
def test_load_deployment_credentials_not_duplicated(deployment_ingestor, sample_deployment_data):
    """Test that deployment credentials are not overwritten on re-load."""
    # Load initial data
    deployment_ingestor.load(sample_deployment_data)

    deployment = deployment_ingestor.db["deployments"].find_one({"name": "test-host-001.psi.ch"})
    original_credentials = deployment_ingestor.db["deployment_credentials"].find_one(
        {"_id": deployment["_id"]}
    )
    original_credential = original_credentials["credential"]

    # Load data again
    deployment_ingestor.load(sample_deployment_data)

    updated_credentials = deployment_ingestor.db["deployment_credentials"].find_one(
        {"_id": deployment["_id"]}
    )
    assert updated_credentials["credential"] == original_credential


@pytest.mark.timeout(60)
def test_load_deployment_access_creation(deployment_ingestor, sample_deployment_data):
    """Test deployment access creation."""
    deployment_ingestor.load(sample_deployment_data)

    deployment = deployment_ingestor.db["deployments"].find_one({"name": "test-host-001.psi.ch"})
    access = deployment_ingestor.db["deployment_access"].find_one({"_id": deployment["_id"]})

    assert access is not None
    assert access["_id"] == deployment["_id"]
    assert access["owner_groups"] == ["admin"]
    assert access["access_groups"] == ["test_deployment_group"]
    assert access["user_read_access"] == []
    assert access["user_write_access"] == []
    assert access["su_read_access"] == []
    assert access["su_write_access"] == []
    assert access["remote_read_access"] == []
    assert access["remote_write_access"] == []


@pytest.mark.timeout(60)
def test_load_deployment_access_document_groups_update(deployment_ingestor, sample_deployment_data):
    """Test that deployment access document groups are updated when changed."""
    # Load initial data
    deployment_ingestor.load(sample_deployment_data)

    # Modify deployment access groups
    modified_data = sample_deployment_data.copy()
    modified_data["test_realm"]["deployments"]["test-host-001.psi.ch"]["deployment_access"] = [
        "updated_group"
    ]

    # Load modified data
    deployment_ingestor.load(modified_data)

    deployment = deployment_ingestor.db["deployments"].find_one({"name": "test-host-001.psi.ch"})
    access = deployment_ingestor.db["deployment_access"].find_one({"_id": deployment["_id"]})

    assert access["access_groups"] == ["updated_group"]


@pytest.mark.timeout(60)
def test_load_minimal_data(deployment_ingestor):
    """Test loading minimal deployment data with default values."""
    minimal_data = {"minimal_realm": {"deployments": {"minimal-host.psi.ch": {"name": "minimal"}}}}
    deployment_ingestor.load(minimal_data)

    # Check realm creation with defaults
    realm = deployment_ingestor.db["realms"].find_one({"realm_id": "minimal_realm"})
    assert realm is not None
    assert realm["managers"] == []  # Default empty list

    # Check deployment creation
    deployment = deployment_ingestor.db["deployments"].find_one({"name": "minimal-host.psi.ch"})
    assert deployment is not None
    assert deployment["access_groups"] == []  # Default empty list

    # Check session creation with defaults
    session = deployment_ingestor.db["sessions"].find_one(
        {"name": "_default_", "deployment_id": str(deployment["_id"])}
    )
    assert session is not None
    assert session["owner_groups"] == []  # Default empty list
    assert session["access_groups"] == []  # Default empty list


@pytest.mark.timeout(60)
def test_load_empty_data(deployment_ingestor):
    """Test loading empty deployment data."""
    deployment_ingestor.load({})

    assert deployment_ingestor.db["realms"].count_documents({}) == 0
    assert deployment_ingestor.db["deployments"].count_documents({}) == 0
    assert deployment_ingestor.db["sessions"].count_documents({}) == 0


@pytest.mark.timeout(60)
def test_load_realm_without_deployments(deployment_ingestor):
    """Test loading realm data without deployments."""
    data = {"realm_no_deployments": {"xname": "x99zz", "managers": ["manager_group"]}}
    deployment_ingestor.load(data)

    realm = deployment_ingestor.db["realms"].find_one({"realm_id": "realm_no_deployments"})
    assert realm is not None

    # Should have no deployments
    deployments = list(
        deployment_ingestor.db["deployments"].find({"realm_id": "realm_no_deployments"})
    )
    assert len(deployments) == 0


@pytest.mark.timeout(60)
@mock.patch("builtins.print")
def test_load_prints_insertion_messages(mock_print, deployment_ingestor, sample_deployment_data):
    """Test that appropriate print messages are displayed during loading."""
    deployment_ingestor.load(sample_deployment_data)

    # Check that print was called for realm and deployment insertions
    print_calls = [call.args[0] for call in mock_print.call_args_list]

    assert any("Inserting realm: test_realm" in call for call in print_calls)
    assert any("Inserting deployment: test-host-001.psi.ch" in call for call in print_calls)


@pytest.mark.timeout(60)
@mock.patch("builtins.print")
def test_load_prints_update_messages(mock_print, deployment_ingestor, sample_deployment_data):
    """Test that appropriate print messages are displayed during updates."""
    # Load initial data
    deployment_ingestor.load(sample_deployment_data)

    # Modify and reload to trigger updates
    modified_data = sample_deployment_data.copy()
    modified_data["test_realm"]["deployments"]["test-host-001.psi.ch"]["deployment_access"] = [
        "new_group"
    ]
    modified_data["test_realm"]["deployments"]["test-host-001.psi.ch"]["experiment_access"] = [
        "new_exp_group"
    ]

    mock_print.reset_mock()
    deployment_ingestor.load(modified_data)

    print_calls = [call.args[0] for call in mock_print.call_args_list]

    assert any(
        "Updating deployment access groups: test-host-001.psi.ch" in call for call in print_calls
    )
    assert any(
        "Updating the access groups for the default session: test-host-001.psi.ch" in call
        for call in print_calls
    )
    assert any(
        "Updating access groups of DeploymentAccess: test-host-001.psi.ch" in call
        for call in print_calls
    )


@pytest.mark.timeout(60)
def test_load_realistic_yaml_structure(deployment_ingestor):
    """Test loading data that matches the real YAML structure."""
    realistic_data = {
        "cSAXS": {
            "xname": "x12sa",
            "managers": ["unx-sls_x12sa_bs"],
            "deployments": {
                "x12sa-bec-001.psi.ch": {
                    "name": "production",
                    "description": "Primary deployment for cSAXS",
                    "deployment_access": ["unx-sls_x12sa_bs"],
                    "experiment_access": ["unx-sls_x12sa_bs"],
                },
                "x12sa-bec-002.psi.ch": {
                    "name": "test",
                    "description": "Test environment for cSAXS",
                    "deployment_access": ["unx-sls_x12sa_bs"],
                    "experiment_access": ["unx-sls_x12sa_bs"],
                },
            },
        }
    }

    deployment_ingestor.load(realistic_data)

    # Verify realm
    realm = deployment_ingestor.db["realms"].find_one({"realm_id": "cSAXS"})
    assert realm["xname"] == "x12sa"
    assert realm["managers"] == ["unx-sls_x12sa_bs"]

    # Verify deployments
    deployments = list(deployment_ingestor.db["deployments"].find({"realm_id": "cSAXS"}))
    assert len(deployments) == 2

    prod_deployment = deployment_ingestor.db["deployments"].find_one(
        {"name": "x12sa-bec-001.psi.ch"}
    )
    test_deployment = deployment_ingestor.db["deployments"].find_one(
        {"name": "x12sa-bec-002.psi.ch"}
    )

    assert prod_deployment is not None
    assert test_deployment is not None

    # Verify sessions
    prod_session = deployment_ingestor.db["sessions"].find_one(
        {"name": "_default_", "deployment_id": str(prod_deployment["_id"])}
    )
    test_session = deployment_ingestor.db["sessions"].find_one(
        {"name": "_default_", "deployment_id": str(test_deployment["_id"])}
    )

    assert prod_session is not None
    assert test_session is not None
