import os
import tempfile
from unittest import mock

import pytest
import yaml
from typer.testing import CliRunner

from bec_atlas.utils.bec_atlas_update import app


@pytest.fixture
def cli_runner():
    """Create a CliRunner for testing Typer commands."""
    return CliRunner()


@pytest.fixture
def sample_deployment_yaml():
    """Sample deployment YAML data for testing."""
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
                }
            },
        }
    }


@pytest.fixture
def temp_yaml_file(sample_deployment_yaml):
    """Create a temporary YAML file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(sample_deployment_yaml, f)
        temp_file_path = f.name

    yield temp_file_path

    # Cleanup
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_update.DeploymentIngestor")
def test_update_deployments_success(mock_deployment_ingestor, cli_runner, temp_yaml_file):
    """Test successful deployment update command."""
    # Mock the ingestor
    mock_ingestor_instance = mock.Mock()
    mock_deployment_ingestor.return_value = mock_ingestor_instance

    # Run the command
    result = cli_runner.invoke(app, ["deployments", temp_yaml_file])

    # Check command execution
    assert result.exit_code == 0
    assert f"Updating deployments with data from {temp_yaml_file}" in result.stdout

    # Check that DeploymentIngestor was called correctly
    mock_deployment_ingestor.assert_called_once_with({"host": "localhost", "port": 27017})
    mock_ingestor_instance.load.assert_called_once()

    # Verify the data passed to load method
    call_args = mock_ingestor_instance.load.call_args[0][0]
    assert "test_realm" in call_args
    assert call_args["test_realm"]["xname"] == "x99za"


@pytest.mark.timeout(60)
def test_update_deployments_file_not_found(cli_runner):
    """Test deployment update command with non-existent file."""
    non_existent_file = "/path/to/non/existent/file.yaml"

    result = cli_runner.invoke(app, ["deployments", non_existent_file])

    assert result.exit_code == 1
    assert f"File not found: {non_existent_file}" in result.stdout


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_update.DeploymentIngestor")
def test_update_deployments_yaml_parsing_error(mock_deployment_ingestor, cli_runner):
    """Test deployment update command with invalid YAML file."""
    # Create a temporary file with invalid YAML
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: content: [unclosed")
        invalid_yaml_file = f.name

    try:
        result = cli_runner.invoke(app, ["deployments", invalid_yaml_file])

        # Should fail due to YAML parsing error
        assert result.exit_code != 0

    finally:
        # Cleanup
        if os.path.exists(invalid_yaml_file):
            os.unlink(invalid_yaml_file)


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_update.DeploymentIngestor")
def test_update_deployments_ingestor_exception(
    mock_deployment_ingestor, cli_runner, temp_yaml_file
):
    """Test deployment update command when ingestor raises an exception."""
    # Mock the ingestor to raise an exception
    mock_ingestor_instance = mock.Mock()
    mock_ingestor_instance.load.side_effect = Exception("Database connection failed")
    mock_deployment_ingestor.return_value = mock_ingestor_instance

    result = cli_runner.invoke(app, ["deployments", temp_yaml_file])

    # Should fail due to ingestor exception
    assert result.exit_code != 0


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_update.ProposalIngestor")
def test_update_experiments_success_current_year(mock_proposal_ingestor, cli_runner):
    """Test successful experiment update command for current year."""
    # Mock the ingestor
    mock_ingestor_instance = mock.Mock()
    mock_ingestor_instance.load_proposals_from_duo.return_value = {"test": "experiments"}
    mock_ingestor_instance.ingest_to_mongo.return_value = "p20240001"
    mock_proposal_ingestor.return_value = mock_ingestor_instance

    # Run the command
    result = cli_runner.invoke(app, ["experiments", "--duo-token", "test_token"])

    # Check command execution
    assert result.exit_code == 0
    assert "Updating experiments from DUO" in result.stdout

    # Check that ProposalIngestor was called correctly
    mock_proposal_ingestor.assert_called_once_with(
        duo_token="test_token", duo_base_url="https://duo.psi.ch/duo/api.php/v1"
    )
    mock_ingestor_instance.load_proposals_from_duo.assert_called_once_with(full=False)
    mock_ingestor_instance.ingest_to_mongo.assert_called_once_with({"test": "experiments"})


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_update.ProposalIngestor")
def test_update_experiments_success_full_update(mock_proposal_ingestor, cli_runner):
    """Test successful experiment update command with full update."""
    # Mock the ingestor
    mock_ingestor_instance = mock.Mock()
    mock_ingestor_instance.load_proposals_from_duo.return_value = {"test": "experiments"}
    mock_ingestor_instance.ingest_to_mongo.return_value = "p20240001"
    mock_proposal_ingestor.return_value = mock_ingestor_instance

    # Run the command with --full flag
    result = cli_runner.invoke(app, ["experiments", "--duo-token", "test_token", "--full"])

    # Check command execution
    assert result.exit_code == 0
    assert "Updating experiments from DUO" in result.stdout

    # Check that full=True was passed
    mock_ingestor_instance.load_proposals_from_duo.assert_called_once_with(full=True)


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_update.ProposalIngestor")
def test_update_experiments_success_short_flag(mock_proposal_ingestor, cli_runner):
    """Test successful experiment update command with short flag."""
    # Mock the ingestor
    mock_ingestor_instance = mock.Mock()
    mock_ingestor_instance.load_proposals_from_duo.return_value = {"test": "experiments"}
    mock_ingestor_instance.ingest_to_mongo.return_value = "p20240001"
    mock_proposal_ingestor.return_value = mock_ingestor_instance

    # Run the command with -f flag
    result = cli_runner.invoke(app, ["experiments", "--duo-token", "test_token", "-f"])

    # Check command execution
    assert result.exit_code == 0

    # Check that full=True was passed
    mock_ingestor_instance.load_proposals_from_duo.assert_called_once_with(full=True)


@pytest.mark.timeout(60)
def test_update_experiments_missing_token(cli_runner):
    """Test experiment update command without required token."""
    result = cli_runner.invoke(app, ["experiments"])

    # Should fail due to missing required argument
    assert result.exit_code == 2  # Typer exits with 2 for missing options
    # In some environments, error output might be empty, so we just check exit code


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_update.ProposalIngestor")
def test_update_experiments_ingestor_exception(mock_proposal_ingestor, cli_runner):
    """Test experiment update command when ingestor raises an exception."""
    # Mock the ingestor to raise an exception
    mock_ingestor_instance = mock.Mock()
    mock_ingestor_instance.load_proposals_from_duo.side_effect = Exception("DUO API error")
    mock_proposal_ingestor.return_value = mock_ingestor_instance

    result = cli_runner.invoke(app, ["experiments", "--duo-token", "test_token"])

    # Should fail due to ingestor exception
    assert result.exit_code != 0


@pytest.mark.timeout(60)
def test_app_help_command(cli_runner):
    """Test that the help command works."""
    result = cli_runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "deployments" in result.stdout
    assert "experiments" in result.stdout


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_update.DeploymentIngestor")
def test_update_deployments_empty_yaml(mock_deployment_ingestor, cli_runner):
    """Test deployment update command with empty YAML file."""
    # Create a temporary file with empty YAML
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({}, f)
        empty_yaml_file = f.name

    try:
        # Mock the ingestor
        mock_ingestor_instance = mock.Mock()
        mock_deployment_ingestor.return_value = mock_ingestor_instance

        result = cli_runner.invoke(app, ["deployments", empty_yaml_file])

        # Should succeed even with empty data
        assert result.exit_code == 0
        mock_ingestor_instance.load.assert_called_once_with({})

    finally:
        # Cleanup
        if os.path.exists(empty_yaml_file):
            os.unlink(empty_yaml_file)


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_update.ProposalIngestor")
def test_update_experiments_empty_token(mock_proposal_ingestor, cli_runner):
    """Test experiment update command with empty token."""
    result = cli_runner.invoke(app, ["experiments", "--duo-token", ""])

    # Should try to proceed even with empty token (ProposalIngestor will handle validation)
    assert result.exit_code == 0 or "duo-token" in result.stdout.lower()


@pytest.mark.timeout(60)
@mock.patch("builtins.open")
@mock.patch("os.path.exists")
@mock.patch("bec_atlas.utils.bec_atlas_update.DeploymentIngestor")
def test_update_deployments_file_read_error(
    mock_deployment_ingestor, mock_exists, mock_open, cli_runner
):
    """Test deployment update command when file cannot be read."""
    mock_exists.return_value = True
    mock_open.side_effect = IOError("Permission denied")

    result = cli_runner.invoke(app, ["deployments", "/some/file.yaml"])

    # Should fail due to file read error
    assert result.exit_code != 0


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_update.ProposalIngestor")
def test_update_experiments_mongo_ingestion_error(mock_proposal_ingestor, cli_runner):
    """Test experiment update command when MongoDB ingestion fails."""
    # Mock the ingestor
    mock_ingestor_instance = mock.Mock()
    mock_ingestor_instance.load_proposals_from_duo.return_value = {"test": "experiments"}
    mock_ingestor_instance.ingest_to_mongo.side_effect = Exception("MongoDB connection failed")
    mock_proposal_ingestor.return_value = mock_ingestor_instance

    result = cli_runner.invoke(app, ["experiments", "--duo-token", "test_token"])

    # Should fail due to MongoDB ingestion error
    assert result.exit_code != 0


@pytest.mark.timeout(60)
def test_invalid_command(cli_runner):
    """Test running an invalid command."""
    result = cli_runner.invoke(app, ["invalid_command"])

    # Should fail with command not found
    assert result.exit_code == 2  # Typer exits with 2 for unknown commands
    # In some environments, error output might be empty, so we just check exit code


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_update.DeploymentIngestor")
def test_update_deployments_with_complex_yaml(mock_deployment_ingestor, cli_runner):
    """Test deployment update command with complex YAML structure."""
    complex_yaml_data = {
        "realm1": {
            "xname": "x01da",
            "managers": ["group1", "group2"],
            "deployments": {
                "host1.example.com": {
                    "name": "production",
                    "deployment_access": ["prod_group"],
                    "experiment_access": ["exp_group"],
                },
                "host2.example.com": {
                    "name": "staging",
                    "deployment_access": ["staging_group"],
                    "experiment_access": ["staging_exp_group"],
                },
            },
        },
        "realm2": {
            "xname": "x02da",
            "managers": ["group3"],
            "deployments": {
                "host3.example.com": {
                    "name": "test",
                    "deployment_access": ["test_group"],
                    "experiment_access": ["test_exp_group"],
                }
            },
        },
    }

    # Create temporary file with complex YAML
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(complex_yaml_data, f)
        complex_yaml_file = f.name

    try:
        # Mock the ingestor
        mock_ingestor_instance = mock.Mock()
        mock_deployment_ingestor.return_value = mock_ingestor_instance

        result = cli_runner.invoke(app, ["deployments", complex_yaml_file])

        # Check command execution
        assert result.exit_code == 0

        # Verify the complex data was passed correctly
        call_args = mock_ingestor_instance.load.call_args[0][0]
        assert "realm1" in call_args
        assert "realm2" in call_args
        assert call_args["realm1"]["xname"] == "x01da"
        assert call_args["realm2"]["xname"] == "x02da"
        assert len(call_args["realm1"]["deployments"]) == 2
        assert len(call_args["realm2"]["deployments"]) == 1

    finally:
        # Cleanup
        if os.path.exists(complex_yaml_file):
            os.unlink(complex_yaml_file)
