from unittest import mock

import pytest
from bec_lib import messages
from bec_lib.redis_connector import MessageObject

from bec_atlas.ingestor.message_service_ingestor import MessageServiceIngestor
from bec_atlas.ingestor.signal.model import (
    SignalEventMessage,
    SignalGroupInfo,
    SignalRecipientAddress,
)


@pytest.fixture
def signal_manager(backend):
    """Create a SignalManager using the real backend configuration."""
    client, app = backend
    app.redis_websocket.users = {}

    # Patch only the external dependencies (HTTP requests and event subscriber)
    with (
        mock.patch("bec_atlas.ingestor.signal_manager.EventSubscriber") as mock_subscriber,
        mock.patch("bec_atlas.ingestor.signal_manager.requests.Session") as mock_session,
    ):

        mock_subscriber.return_value = mock.Mock()
        mock_session.return_value = mock.Mock()

        # Create the full ingestor which will create the SignalManager
        ingestor = MessageServiceIngestor(config=app.config)
        yield ingestor.signal_manager
        ingestor.shutdown()


def test_get_text_from_message(signal_manager):
    msg = messages.MessagingServiceMessage(
        service_name="signal",
        message=[
            messages.MessagingServiceTextContent(content="Hello"),
            messages.MessagingServiceTextContent(content="World"),
        ],
        scope=["user1"],
    )

    assert signal_manager.get_text_from_message(msg) == "Hello\nWorld"


def test_process_posts_payload(signal_manager):
    msg = messages.MessagingServiceMessage(
        service_name="signal",
        message=[messages.MessagingServiceTextContent(content="Hello, Signal!")],
        scope=["user1", "user2"],
    )

    deployment_info = messages.DeploymentInfoMessage(
        deployment_id="test_deployment",
        name="Test Deployment",
        messaging_config=messages.MessagingConfig(
            signal=messages.MessagingServiceScopeConfig(enabled=True, default=None),
            scilog=messages.MessagingServiceScopeConfig(enabled=True, default=None),
            teams=messages.MessagingServiceScopeConfig(enabled=False, default=None),
        ),
    )
    with mock.patch.object(
        signal_manager, "get_group_id_for_deployment", return_value="test_group_id"
    ):
        with mock.patch.object(signal_manager, "post") as mock_post:
            signal_manager.process(msg, deployment_info)

    mock_post.assert_called()
    payload = mock_post.call_args.args[0]
    assert payload["jsonrpc"] == "2.0"
    assert payload["method"] == "send"
    assert payload["params"]["message"] == "Hello, Signal!"
    assert payload["params"]["groupId"] == "test_group_id"


def test_handle_signal_link_request_stores_pending(signal_manager):
    msg_obj = MessageObject(
        value=messages.VariableMessage(
            value={"number": "+491234", "session": {"id": 1}, "session_id": "session-1"}
        ),
        topic="signal_link_requests",
    )

    with mock.patch.object(signal_manager, "send_signal_link_request") as mock_send:
        signal_manager._handle_signal_link_request(msg_obj, signal_manager)

    assert "+491234" in signal_manager.pending_signal_requests
    assert signal_manager.pending_signal_requests["+491234"]["session_id"] == "session-1"
    assert signal_manager.pending_signal_requests["+491234"]["session"] == {"id": 1}
    assert signal_manager.pending_signal_requests["+491234"]["number"] == "+491234"
    mock_send.assert_called_once_with("+491234")


def test_check_pending_signal_link_request_with_group_link(signal_manager):
    signal_manager.pending_signal_requests["+491234"] = {
        "session_id": "session-1",
        "session": {"id": 1},
        "number": "+491234",
    }
    event = {
        "account": "+491234",
        "envelope": {
            "sourceNumber": "+491234",
            "timestamp": 1,
            "serverReceivedTimestamp": 1,
            "serverDeliveredTimestamp": 1,
            "dataMessage": {"timestamp": 1, "message": "https://signal.group/abcd some text"},
        },
    }

    signal_event = SignalEventMessage(**event)

    with mock.patch.object(signal_manager, "complete_signal_linking") as mock_complete:
        result = signal_manager.check_pending_signal_link_request(signal_event)

    assert result is True
    mock_complete.assert_called_once_with("+491234", "https://signal.group/abcd")


def test_check_pending_signal_link_request_ignores_non_link(signal_manager):
    signal_manager.pending_signal_requests["+491234"] = {
        "session_id": "session-1",
        "session": {"id": 1},
        "number": "+491234",
    }
    event = {
        "account": "+491234",
        "envelope": {
            "sourceNumber": "+491234",
            "timestamp": 1,
            "serverReceivedTimestamp": 1,
            "serverDeliveredTimestamp": 1,
            "dataMessage": {"timestamp": 1, "message": "not a link"},
        },
    }

    signal_event = SignalEventMessage(**event)

    with mock.patch.object(signal_manager, "complete_signal_linking") as mock_complete:
        result = signal_manager.check_pending_signal_link_request(signal_event)

    assert result is False
    mock_complete.assert_not_called()


def test_complete_signal_linking_calls_join_group(signal_manager):
    signal_manager.pending_signal_requests["+491234"] = {
        "session_id": "session-1",
        "session": {"id": 1},
        "number": "+491234",
    }

    signal_manager.complete_signal_linking("+491234", "https://signal.group/abcd")

    expected_join_call = mock.call(
        f"{signal_manager.group_manager.host}/api/v1/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "joinGroup",
            "params": {"uri": "https://signal.group/abcd"},
            "id": 1,
        },
        timeout=10,
    )
    assert expected_join_call in signal_manager.group_manager.session.post.mock_calls

    expected_confirm_call = mock.call(
        f"{signal_manager.host}/api/v1/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "send",
            "params": {
                "message": "Your Signal group has been successfully linked.",
                "recipients": ["+491234"],
            },
        },
        timeout=10,
    )
    assert expected_confirm_call in signal_manager.session.post.mock_calls
    assert "+491234" not in signal_manager.pending_signal_requests


def test_send_signal_link_request_without_pending(signal_manager):
    with mock.patch.object(signal_manager, "post") as mock_post:
        signal_manager.send_signal_link_request("+491234")

    mock_post.assert_not_called()


def test_get_group_id_for_deployment_prefers_active_session(signal_manager):
    deployment_info = messages.DeploymentInfoMessage(
        deployment_id="dep-1",
        name="Test Deployment",
        messaging_config=messages.MessagingConfig(
            signal=messages.MessagingServiceScopeConfig(enabled=True, default=None),
            scilog=messages.MessagingServiceScopeConfig(enabled=False, default=None),
            teams=messages.MessagingServiceScopeConfig(enabled=False, default=None),
        ),
        messaging_services=[
            messages.SignalServiceInfo(
                id="signal-deployment",
                service_type="signal",
                enabled=True,
                group_id="group-deployment",
                group_link="https://signal.group/deployment",
                scope="user1",
            )
        ],
        active_session=messages.SessionInfoMessage(
            id="session-1",
            deployment_id="dep-1",
            name="Session 1",
            messaging_services=[
                messages.SignalServiceInfo(
                    id="signal-session",
                    service_type="signal",
                    enabled=True,
                    group_id="group-session",
                    group_link="https://signal.group/session",
                    scope="user1",
                )
            ],
        ),
    )

    assert signal_manager.get_group_id_for_deployment(deployment_info, "user1") == "group-session"


def test_check_direct_mention_calls_handler(signal_manager):
    event = {
        "account": "+491234",
        "envelope": {
            "sourceNumber": "+491234",
            "timestamp": 1,
            "serverReceivedTimestamp": 1,
            "serverDeliveredTimestamp": 1,
            "dataMessage": {
                "timestamp": 1,
                "message": "hello",
                "mentions": [{"number": signal_manager.number, "start": 0, "length": 3}],
                "groupInfo": {
                    "groupId": "group-1",
                    "groupName": "Group",
                    "revision": 1,
                    "type": "DELIVER",
                },
            },
        },
    }

    signal_event = SignalEventMessage(**event)

    with mock.patch.object(signal_manager, "handle_direct_message") as mock_handle:
        result = signal_manager.check_direct_mention(signal_event)

    assert result is True
    mock_handle.assert_called_once_with(signal_event)


def test_check_direct_mention_without_mentions(signal_manager):
    event = {
        "account": "+491234",
        "envelope": {
            "sourceNumber": "+491234",
            "timestamp": 1,
            "serverReceivedTimestamp": 1,
            "serverDeliveredTimestamp": 1,
            "dataMessage": {
                "timestamp": 1,
                "message": "hello",
                "mentions": [],
                "groupInfo": {
                    "groupId": "group-1",
                    "groupName": "Group",
                    "revision": 1,
                    "type": "DELIVER",
                },
            },
        },
    }

    signal_event = SignalEventMessage(**event)

    with mock.patch.object(signal_manager, "handle_direct_message") as mock_handle:
        result = signal_manager.check_direct_mention(signal_event)

    assert result is False
    mock_handle.assert_not_called()


def test_complete_signal_linking_banned_user_sends_message(signal_manager):
    signal_manager.pending_signal_requests["+491234"] = {
        "deployment_id": "dep-1",
        "number": "+491234",
    }

    group = SignalGroupInfo(
        id="group-1",
        name="Group",
        groupInviteLink="https://signal.group/abcd",
        members=[],
        pendingMembers=[],
        requestingMembers=[],
        admins=[],
        banned=[SignalRecipientAddress(number=signal_manager.number)],
        permissionAddMember="EVERY_MEMBER",
        permissionEditDetails="EVERY_MEMBER",
        permissionSendMessage="EVERY_MEMBER",
    )

    with (
        mock.patch.object(signal_manager.group_manager, "join_group", return_value=None),
        mock.patch.object(signal_manager.group_manager, "get_all_groups", return_value=[group]),
    ):
        signal_manager.complete_signal_linking("+491234", "https://signal.group/abcd")

    expected_call = mock.call(
        f"{signal_manager.host}/api/v1/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "send",
            "params": {
                "message": "Your link request has been received, but BEC is currently banned from the group. Please add BEC back to the group.",
                "recipients": ["+491234"],
            },
        },
        timeout=10,
    )
    assert expected_call in signal_manager.session.post.mock_calls


def test_complete_signal_linking_no_group_sends_message(signal_manager):
    signal_manager.pending_signal_requests["+491234"] = {
        "deployment_id": "dep-1",
        "number": "+491234",
    }

    with (
        mock.patch.object(signal_manager.group_manager, "join_group", return_value=None),
        mock.patch.object(signal_manager.group_manager, "get_all_groups", return_value=[]),
    ):
        signal_manager.complete_signal_linking("+491234", "https://signal.group/abcd")

    expected_call = mock.call(
        f"{signal_manager.host}/api/v1/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "send",
            "params": {
                "message": "Your link request has been received, but no matching group was found on the Signal server. Please make sure to send a valid group link.",
                "recipients": ["+491234"],
            },
        },
        timeout=10,
    )
    assert expected_call in signal_manager.session.post.mock_calls


def test_handle_signal_message_update_join(signal_manager):
    msg_obj = MessageObject(
        value=messages.VariableMessage(
            value={"action": "join", "group_link": "https://signal.group/abcd"}
        ),
        topic="signal_group_updates",
    )

    with (
        mock.patch.object(
            signal_manager.group_manager, "join_group", return_value="group-1"
        ) as mock_join,
        mock.patch.object(signal_manager, "send_random_message") as mock_send,
    ):
        signal_manager._handle_signal_message_update(msg_obj, signal_manager)

    mock_join.assert_called_once_with("https://signal.group/abcd")
    mock_send.assert_called_once_with("group-1", "enter")


def test_handle_signal_message_update_leave(signal_manager):
    msg_obj = MessageObject(
        value=messages.VariableMessage(value={"action": "leave", "group_id": "group-1"}),
        topic="signal_group_updates",
    )

    with (
        mock.patch.object(signal_manager, "send_random_message") as mock_send,
        mock.patch.object(signal_manager.group_manager, "leave_group") as mock_leave,
    ):
        signal_manager._handle_signal_message_update(msg_obj, signal_manager)

    mock_send.assert_called_once_with("group-1", "exit")
    mock_leave.assert_called_once_with("group-1")
