import os
import tempfile
from unittest import mock

import pytest
import requests
from typer.testing import CliRunner

from bec_atlas.utils.bec_atlas_get_key import app


@pytest.fixture
def cli_runner():
    """Create a CliRunner for testing Typer commands."""
    return CliRunner()


@pytest.fixture
def mock_env_response():
    """Sample environment file response for testing."""
    return """ATLAS_HOST=localhost:6380
ATLAS_DEPLOYMENT=507f1f77bcf86cd799439011
ATLAS_KEY=test_key_123456789"""


@pytest.fixture
def temp_output_file():
    """Create a temporary output file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        temp_file_path = f.name

    yield temp_file_path

    # Cleanup
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_get_key.requests.get")
@mock.patch("bec_atlas.utils.bec_atlas_get_key.requests.post")
def test_successful_execution(mock_post, mock_get, cli_runner, mock_env_response, temp_output_file):
    """Test successful execution."""
    # Mock login response
    mock_login_response = mock.Mock()
    mock_login_response.status_code = 200
    mock_login_response.text = '"test_token_123"'
    mock_post.return_value = mock_login_response

    # Mock env file response
    mock_env_response_obj = mock.Mock()
    mock_env_response_obj.status_code = 200
    mock_env_response_obj.text = mock_env_response
    mock_get.return_value = mock_env_response_obj

    # Run the command
    result = cli_runner.invoke(
        app,
        [
            "--user",
            "testuser",
            "--password",
            "testpass",
            "--deployment",
            "test-deployment",
            "--output",
            temp_output_file,
        ],
    )

    # Check command execution
    assert result.exit_code == 0

    # Check that the file was written correctly
    with open(temp_output_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert content == mock_env_response


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_get_key.requests.post")
def test_login_failure_returns_error_code(mock_post, cli_runner):
    """Test login failure scenario."""
    # Mock failed login response
    mock_login_response = mock.Mock()
    mock_login_response.status_code = 401
    mock_login_response.text = "Unauthorized"
    mock_post.return_value = mock_login_response

    # Run the command
    result = cli_runner.invoke(
        app, ["--user", "testuser", "--password", "wrongpass", "--deployment", "test-host"]
    )

    # Check command execution
    assert result.exit_code == 1


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_get_key.requests.get")
@mock.patch("bec_atlas.utils.bec_atlas_get_key.requests.post")
def test_env_file_retrieval_failure_returns_error_code(mock_post, mock_get, cli_runner):
    """Test environment file retrieval failure."""
    # Mock successful login
    mock_login_response = mock.Mock()
    mock_login_response.status_code = 200
    mock_login_response.text = '"test_token"'
    mock_post.return_value = mock_login_response

    # Mock failed env file response
    mock_env_response = mock.Mock()
    mock_env_response.status_code = 404
    mock_env_response.text = "Deployment not found"
    mock_get.return_value = mock_env_response

    # Run the command
    result = cli_runner.invoke(
        app, ["--user", "testuser", "--password", "testpass", "--deployment", "nonexistent"]
    )

    # Check command execution
    assert result.exit_code == 1


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_get_key.requests.post")
def test_network_error_returns_error_code(mock_post, cli_runner):
    """Test network error scenario."""
    # Mock network error
    mock_post.side_effect = requests.exceptions.ConnectionError("Network unreachable")

    # Run the command
    result = cli_runner.invoke(
        app, ["--user", "testuser", "--password", "testpass", "--deployment", "test-host"]
    )

    # Check command execution
    assert result.exit_code == 1


@pytest.mark.timeout(60)
def test_help_command_shows_usage(cli_runner):
    """Test that the help command works."""
    result = cli_runner.invoke(app, ["--help"])

    assert result.exit_code == 0


@pytest.mark.timeout(60)
@mock.patch("bec_atlas.utils.bec_atlas_get_key.requests.post")
def test_keyboard_interrupt_returns_error_code(mock_post, cli_runner):
    """Test keyboard interrupt scenario."""
    # Mock keyboard interrupt
    mock_post.side_effect = KeyboardInterrupt()

    # Run the command
    result = cli_runner.invoke(
        app, ["--user", "testuser", "--password", "testpass", "--deployment", "test-host"]
    )

    # Check command execution
    assert result.exit_code == 1
