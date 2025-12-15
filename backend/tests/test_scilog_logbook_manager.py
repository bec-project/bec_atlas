import os
from unittest import mock

import pytest
from bec_lib import messages
from scilog.models import Logbook

from bec_atlas.ingestor.scilog_logbook_manager import SciLogLogbookManager


@pytest.fixture
def mock_scilog():
    """Create a mock SciLog instance."""
    with mock.patch("bec_atlas.ingestor.scilog_logbook_manager.scilog.SciLog") as MockSciLog:
        mock_instance = MockSciLog.return_value
        mock_instance.get_logbooks.return_value = []
        yield mock_instance


@pytest.fixture
def logbook_manager(mock_scilog, tmp_path):
    """Create a SciLogLogbookManager instance with mocked SciLog."""
    config = {"username": "test_user", "password": "test_password"}
    manager = SciLogLogbookManager(config=config, temp_dir=str(tmp_path))
    return manager


@pytest.fixture
def sample_logbook():
    """Create a sample logbook object."""
    logbook = Logbook(
        id="logbook_123",
        name="Test Logbook",
        updateACL=["p20240001"],
        readACL=["p20240001"],
        createACL=["p20240001"],
        deleteACL=["p20240001"],
        adminACL=["admin"],
        ownerGroup="p20240001",
        thumbnail="",
        location="",
        isPrivate=False,
        expiresAt=None,
        description="Test logbook for unit tests",
    )
    return logbook


@pytest.fixture
def sample_deployment_info():
    """Create a sample deployment info message."""
    return messages.DeploymentInfoMessage(
        deployment_id="678aa8d4875568640bd92176",
        name="Test Deployment",
        messaging_config=messages.MessagingConfig(
            signal=messages.MessagingServiceScopeConfig(enabled=False),
            teams=messages.MessagingServiceScopeConfig(enabled=False),
            scilog=messages.MessagingServiceScopeConfig(enabled=True, default="deployment_scope"),
        ),
        messaging_services=[
            messages.SciLogServiceInfo(
                id="scilog_service_1",
                service_type="scilog",
                enabled=True,
                logbook_id="logbook_123",
                scope="deployment_scope",
            )
        ],
    )


@pytest.fixture
def sample_deployment_with_session():
    """Create a sample deployment info with active session."""
    return messages.DeploymentInfoMessage(
        deployment_id="678aa8d4875568640bd92176",
        name="Test Deployment",
        messaging_config=messages.MessagingConfig(
            signal=messages.MessagingServiceScopeConfig(enabled=False),
            teams=messages.MessagingServiceScopeConfig(enabled=False),
            scilog=messages.MessagingServiceScopeConfig(enabled=True, default="deployment_scope"),
        ),
        messaging_services=[
            messages.SciLogServiceInfo(
                id="scilog_service_1",
                service_type="scilog",
                enabled=True,
                logbook_id="logbook_123",
                scope="deployment_scope",
            )
        ],
        active_session=messages.SessionInfoMessage(
            name="Test Session",
            messaging_services=[
                messages.SciLogServiceInfo(
                    id="scilog_service_2",
                    service_type="scilog",
                    enabled=True,
                    logbook_id="logbook_456",
                    scope="session_scope",
                )
            ],
        ),
    )


@pytest.mark.timeout(60)
def test_init_with_config(mock_scilog, tmp_path):
    """Test initialization with config."""
    config = {"username": "test_user", "password": "test_password"}
    manager = SciLogLogbookManager(config=config, temp_dir=str(tmp_path))
    assert manager.config == config
    assert manager.scilog is not None
    assert manager.temp_dir == str(tmp_path)


@pytest.mark.timeout(60)
def test_init_with_token(mock_scilog, tmp_path):
    """Test initialization with token."""
    token = "test_token"
    config = {"username": "test_user", "password": "test_password"}
    manager = SciLogLogbookManager(config=config, token=token, temp_dir=str(tmp_path))
    assert manager.token == token
    assert manager.config == config
    assert manager.temp_dir == str(tmp_path)


@pytest.mark.timeout(60)
def test_init_without_config_or_token():
    """Test that initialization fails without config or token."""
    with pytest.raises(ValueError, match="Either token or config must be provided"):
        SciLogLogbookManager()


@pytest.mark.timeout(60)
def test_fetch_logbooks_for_pgroup(logbook_manager, mock_scilog, sample_logbook):
    """Test fetching logbooks for a proposal group."""
    mock_scilog.get_logbooks.return_value = [sample_logbook]

    logbooks = logbook_manager.fetch_logbooks_for_pgroup("p20240001")

    assert len(logbooks) == 1
    assert logbooks[0].id == "logbook_123"
    mock_scilog.get_logbooks.assert_called_once_with(where={"updateACL": {"in": ["p20240001"]}})


@pytest.mark.timeout(60)
def test_get_logbook_id_with_deployment_scope(logbook_manager, sample_deployment_info):
    """Test get_logbook_id with deployment-level scilog service."""
    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[messages.MessagingServiceTextContent(content="Test message")],
        scope="deployment_scope",
    )

    logbook_ids = logbook_manager.get_logbook_id(msg, sample_deployment_info)

    assert logbook_ids is not None
    assert len(logbook_ids) == 1
    assert logbook_ids[0] == "logbook_123"


@pytest.mark.timeout(60)
def test_get_logbook_id_with_session_scope(logbook_manager, sample_deployment_with_session):
    """Test get_logbook_id with session-level scilog service."""
    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[messages.MessagingServiceTextContent(content="Test message")],
        scope="session_scope",
    )

    logbook_ids = logbook_manager.get_logbook_id(msg, sample_deployment_with_session)

    assert logbook_ids is not None
    assert len(logbook_ids) == 1
    assert logbook_ids[0] == "logbook_456"


@pytest.mark.timeout(60)
def test_get_logbook_id_with_multiple_scopes(logbook_manager, sample_deployment_with_session):
    """Test get_logbook_id with multiple scopes matching deployment and session."""
    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[messages.MessagingServiceTextContent(content="Test message")],
        scope=["deployment_scope", "session_scope"],
    )

    logbook_ids = logbook_manager.get_logbook_id(msg, sample_deployment_with_session)

    assert logbook_ids is not None
    assert len(logbook_ids) == 2
    assert "logbook_123" in logbook_ids
    assert "logbook_456" in logbook_ids


@pytest.mark.timeout(60)
def test_get_logbook_id_with_invalid_scope(logbook_manager, sample_deployment_info):
    """Test get_logbook_id with scope not in deployment services."""
    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[messages.MessagingServiceTextContent(content="Test message")],
        scope="invalid_scope",
    )

    logbook_ids = logbook_manager.get_logbook_id(msg, sample_deployment_info)

    assert logbook_ids is None


@pytest.mark.timeout(60)
def test_get_logbook_id_with_no_scope(logbook_manager, sample_deployment_info):
    """Test get_logbook_id when message has no scope."""
    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[messages.MessagingServiceTextContent(content="Test message")],
        scope=None,
    )

    logbook_ids = logbook_manager.get_logbook_id(msg, sample_deployment_info)

    assert logbook_ids is None


@pytest.mark.timeout(60)
def test_get_logbook_id_with_disabled_service(logbook_manager):
    """Test get_logbook_id when scilog service is disabled."""
    deployment = messages.DeploymentInfoMessage(
        deployment_id="678aa8d4875568640bd92176",
        name="Test Deployment",
        messaging_config=messages.MessagingConfig(
            signal=messages.MessagingServiceScopeConfig(enabled=False),
            teams=messages.MessagingServiceScopeConfig(enabled=False),
            scilog=messages.MessagingServiceScopeConfig(enabled=False),
        ),
        messaging_services=[
            messages.SciLogServiceInfo(
                id="scilog_service_1",
                service_type="scilog",
                enabled=False,  # Disabled
                logbook_id="logbook_123",
                scope="deployment_scope",
            )
        ],
    )

    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[messages.MessagingServiceTextContent(content="Test message")],
        scope="deployment_scope",
    )

    logbook_ids = logbook_manager.get_logbook_id(msg, deployment)

    assert logbook_ids is None


@pytest.mark.timeout(60)
def test_fetch_logbook_by_id(logbook_manager, mock_scilog, sample_logbook):
    """Test fetching a logbook by ID."""
    mock_scilog.get_logbooks.return_value = [sample_logbook]

    logbook = logbook_manager.fetch_logbook_by_id("logbook_123")

    assert logbook is not None
    assert logbook.id == "logbook_123"
    mock_scilog.get_logbooks.assert_called_once_with(where={"id": "logbook_123"})


@pytest.mark.timeout(60)
def test_fetch_logbook_by_id_not_found(logbook_manager, mock_scilog):
    """Test fetching a logbook by ID that doesn't exist."""
    mock_scilog.get_logbooks.return_value = []

    logbook = logbook_manager.fetch_logbook_by_id("nonexistent_logbook")

    assert logbook is None
    mock_scilog.get_logbooks.assert_called_once_with(where={"id": "nonexistent_logbook"})


@pytest.mark.timeout(60)
def test_fetch_logbook_by_id_caching(logbook_manager, mock_scilog, sample_logbook):
    """Test that fetch_logbook_by_id uses caching."""
    mock_scilog.get_logbooks.return_value = [sample_logbook]

    # First call
    logbook1 = logbook_manager.fetch_logbook_by_id("logbook_123")
    assert logbook1 is not None

    # Second call should use cache
    logbook2 = logbook_manager.fetch_logbook_by_id("logbook_123")
    assert logbook2 is not None

    # Should only call scilog once due to caching
    assert mock_scilog.get_logbooks.call_count == 1


@pytest.mark.timeout(60)
def test_ingest_data_with_text_content(logbook_manager, mock_scilog, sample_logbook):
    """Test ingesting data with text content."""
    mock_scilog.get_logbooks.return_value = [sample_logbook]
    mock_message = mock.Mock()
    mock_scilog.new.return_value = mock_message

    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[
            messages.MessagingServiceTextContent(content="Test message line 1"),
            messages.MessagingServiceTextContent(content="Test message line 2"),
        ],
        scope="deployment_scope",
    )

    logbook_manager.ingest_data(msg, "logbook_123")

    mock_scilog.select_logbook.assert_called_once_with(sample_logbook)
    mock_scilog.new.assert_called_once()
    assert mock_message.add_text.call_count == 2
    mock_message.add_text.assert_any_call("Test message line 1")
    mock_message.add_text.assert_any_call("Test message line 2")
    mock_message.send.assert_called_once()


@pytest.mark.timeout(60)
def test_ingest_data_with_file_content(logbook_manager, mock_scilog, sample_logbook, tmp_path):
    """Test ingesting data with file content."""
    mock_scilog.get_logbooks.return_value = [sample_logbook]
    mock_message = mock.Mock()
    mock_scilog.new.return_value = mock_message

    file_data = b"Test file content"
    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[
            messages.MessagingServiceTextContent(content="Attaching a file"),
            messages.MessagingServiceFileContent(
                filename="test.txt", data=file_data, mime_type="text/plain"
            ),
        ],
        scope="deployment_scope",
    )

    # Track if files were actually created
    created_files = []
    original_add_file = mock_message.add_file

    def track_add_file(file_path):
        created_files.append(file_path)
        # Verify file exists at the time it's added
        assert os.path.exists(file_path), f"File {file_path} should exist when added"
        # Verify file content
        with open(file_path, "rb") as f:
            assert f.read() == file_data, "File content should match"
        return original_add_file(file_path)

    mock_message.add_file = track_add_file

    logbook_manager.ingest_data(msg, "logbook_123")

    mock_scilog.select_logbook.assert_called_once_with(sample_logbook)
    mock_scilog.new.assert_called_once()
    mock_message.add_text.assert_called_once_with("Attaching a file")

    # Verify file was added to message
    assert len(created_files) == 1
    assert "test.txt" in created_files[0]

    mock_message.send.assert_called_once()

    # Verify cleanup happened - files and directories should be removed
    # The temp directory should be empty after cleanup
    assert len(list(tmp_path.iterdir())) == 0


@pytest.mark.timeout(60)
def test_ingest_data_with_tags_content(logbook_manager, mock_scilog, sample_logbook):
    """Test ingesting data with tags content."""
    mock_scilog.get_logbooks.return_value = [sample_logbook]
    mock_message = mock.Mock()
    mock_scilog.new.return_value = mock_message

    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[
            messages.MessagingServiceTextContent(content="Tagged message"),
            messages.MessagingServiceTagsContent(tags=["tag1", "tag2", "tag3"]),
        ],
        scope="deployment_scope",
    )

    logbook_manager.ingest_data(msg, "logbook_123")

    mock_scilog.select_logbook.assert_called_once_with(sample_logbook)
    mock_scilog.new.assert_called_once()
    mock_message.add_text.assert_called_once_with("Tagged message")
    mock_message.add_tag.assert_called_once_with(["tag1", "tag2", "tag3"])
    mock_message.send.assert_called_once()


@pytest.mark.timeout(60)
def test_ingest_data_with_mixed_content(logbook_manager, mock_scilog, sample_logbook, tmp_path):
    """Test ingesting data with mixed content types."""
    mock_scilog.get_logbooks.return_value = [sample_logbook]
    mock_message = mock.Mock()
    mock_scilog.new.return_value = mock_message

    file_data = b"Test file content"
    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[
            messages.MessagingServiceTextContent(content="Message with everything"),
            messages.MessagingServiceFileContent(
                filename="data.csv", data=file_data, mime_type="text/csv"
            ),
            messages.MessagingServiceTagsContent(tags=["experiment", "scan1"]),
        ],
        scope="deployment_scope",
    )

    logbook_manager.ingest_data(msg, "logbook_123")

    mock_scilog.select_logbook.assert_called_once_with(sample_logbook)
    mock_scilog.new.assert_called_once()
    mock_message.add_text.assert_called_once()
    mock_message.add_file.assert_called_once()
    mock_message.add_tag.assert_called_once()
    mock_message.send.assert_called_once()

    # Verify cleanup - temp directory should be empty
    assert len(list(tmp_path.iterdir())) == 0


@pytest.mark.timeout(60)
def test_ingest_data_logbook_not_found(logbook_manager, mock_scilog):
    """Test ingesting data when logbook is not found."""
    mock_scilog.get_logbooks.return_value = []

    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[messages.MessagingServiceTextContent(content="Test message")],
        scope="deployment_scope",
    )

    logbook_manager.ingest_data(msg, "nonexistent_logbook")

    # Should not call select_logbook or new if logbook not found
    mock_scilog.select_logbook.assert_not_called()
    mock_scilog.new.assert_not_called()


@pytest.mark.timeout(60)
def test_process_with_valid_scope(
    logbook_manager, mock_scilog, sample_deployment_info, sample_logbook
):
    """Test process method with valid message scope."""
    mock_scilog.get_logbooks.return_value = [sample_logbook]
    mock_message = mock.Mock()
    mock_scilog.new.return_value = mock_message

    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[messages.MessagingServiceTextContent(content="Test message")],
        scope="deployment_scope",
    )

    logbook_manager.process(msg, sample_deployment_info)

    # Verify ingest_data was called
    mock_scilog.select_logbook.assert_called_once()
    mock_message.send.assert_called_once()


@pytest.mark.timeout(60)
def test_process_with_invalid_scope(logbook_manager, sample_deployment_info):
    """Test process method with invalid message scope."""
    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[messages.MessagingServiceTextContent(content="Test message")],
        scope="invalid_scope",
    )

    with mock.patch.object(logbook_manager, "ingest_data") as mock_ingest:
        logbook_manager.process(msg, sample_deployment_info)

        # ingest_data should not be called for invalid scope
        mock_ingest.assert_not_called()


@pytest.mark.timeout(60)
def test_process_with_multiple_logbooks(
    logbook_manager, mock_scilog, sample_deployment_with_session
):
    """Test process method with multiple valid logbook IDs."""
    sample_logbook1 = Logbook(
        id="logbook_123",
        name="Test Logbook 1",
        updateACL=["p20240001"],
        readACL=["p20240001"],
        createACL=["p20240001"],
        deleteACL=["p20240001"],
        adminACL=["admin"],
        ownerGroup="p20240001",
        thumbnail="",
        location="",
        isPrivate=False,
        expiresAt=None,
        description="Test logbook 1",
    )
    sample_logbook2 = Logbook(
        id="logbook_456",
        name="Test Logbook 2",
        updateACL=["p20240001"],
        readACL=["p20240001"],
        createACL=["p20240001"],
        deleteACL=["p20240001"],
        adminACL=["admin"],
        ownerGroup="p20240001",
        thumbnail="",
        location="",
        isPrivate=False,
        expiresAt=None,
        description="Test logbook 2",
    )

    def get_logbooks_side_effect(where):
        logbook_id = where.get("id")
        if logbook_id == "logbook_123":
            return [sample_logbook1]
        elif logbook_id == "logbook_456":
            return [sample_logbook2]
        return []

    mock_scilog.get_logbooks.side_effect = get_logbooks_side_effect
    mock_message = mock.Mock()
    mock_scilog.new.return_value = mock_message

    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[messages.MessagingServiceTextContent(content="Test message")],
        scope=["deployment_scope", "session_scope"],
    )

    logbook_manager.process(msg, sample_deployment_with_session)

    # Should call ingest_data twice (once for each logbook)
    assert mock_scilog.select_logbook.call_count == 2
    assert mock_message.send.call_count == 2


@pytest.mark.timeout(60)
def test_ingest_data_file_cleanup_on_error(logbook_manager, mock_scilog, sample_logbook, tmp_path):
    """Test that temporary files are cleaned up even if an error occurs."""
    mock_scilog.get_logbooks.return_value = [sample_logbook]
    mock_message = mock.Mock()
    mock_scilog.new.return_value = mock_message

    file_data = b"Test file content"
    msg = messages.MessagingServiceMessage(
        service_name="scilog",
        message=[
            messages.MessagingServiceFileContent(
                filename="test.txt", data=file_data, mime_type="text/plain"
            )
        ],
        scope="deployment_scope",
    )

    # Mock os.remove to simulate an error
    with mock.patch("os.remove", side_effect=OSError("Failed to remove file")):
        logbook_manager.ingest_data(msg, "logbook_123")

        # File should have been created
        mock_message.send.assert_called_once()

        # Despite the error, directory should exist (failed to clean up the file)
        # In this case we expect subdirectories to remain since file removal failed
        assert len(list(tmp_path.iterdir())) > 0
