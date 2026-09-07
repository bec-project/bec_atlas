from unittest import mock

import pytest
from bec_lib import messages
from bec_lib.endpoints import MessageEndpoints

from bec_atlas.ingestor.message_service_ingestor import MessageServiceIngestor


def _deployment_info_message():
    return messages.DeploymentInfoMessage(
        deployment_id="678aa8d4875568640bd92176",
        name="Test Deployment",
        messaging_config=messages.MessagingConfig(
            signal=messages.MessagingServiceScopeConfig(enabled=True, default="signal_service_1"),
            teams=messages.MessagingServiceScopeConfig(enabled=True, default="user1"),
            scilog=messages.MessagingServiceScopeConfig(enabled=True, default="user1"),
        ),
        messaging_services=[
            messages.SignalServiceInfo(
                id="signal_service_1",
                service_type="signal",
                enabled=True,
                group_id="signal_group",
                group_link="https://signal.test",
                scope="user1",
            )
        ],
    )


@pytest.fixture
def ingestor(backend):
    client, app = backend
    app.redis_websocket.users = {}
    with mock.patch(
        "bec_atlas.ingestor.message_service_ingestor.SignalManager"
    ) as MockSignalManager:
        # Exercise handlers directly without starting the background queue consumer.
        with mock.patch.object(MessageServiceIngestor, "start_receiver"):
            ingestor = MessageServiceIngestor(config=app.config)
        MockSignalManager.assert_called_once_with(ingestor, app.config.get("signal", {}))
        yield ingestor
        ingestor.shutdown()


@pytest.fixture
def message_processed(ingestor):
    processed = threading.Event()
    ingestor.signal_manager.process.side_effect = lambda *args, **kwargs: processed.set()
    return processed


def test_process_message(ingestor):
    """
    Test that the process_message method processes a message correctly. This is a very basic test that just checks that the method can be called without errors.
    """
    msg = messages.MessagingServiceMessage(
        service_name="signal",
        message=[messages.MessagingServiceTextContent(content="Hello, Signal!")],
        scope=["user1", "user2"],
    )
    deployment = _deployment_info_message()
    ingestor.process_message(msg, deployment)
    ingestor.signal_manager.process.assert_called_once_with(msg, deployment)


def test_handle_message(ingestor):
    """Load deployment info from Redis, register its subscription, and dispatch the message."""
    deployment = _deployment_info_message()
    deployment_id = deployment.deployment_id
    msg = messages.MessagingServiceMessage(
        service_name="signal",
        message=[messages.MessagingServiceTextContent(content="Hello, Signal!")],
        scope=["user1", "user2"],
    )
    ingestor.redis.xadd(
        MessageEndpoints.atlas_deployment_info(deployment_name=deployment_id), {"data": deployment}
    )
    ingestor.handle_message({"data": msg}, ingestor.get_stream_key(deployment_id).endpoint)

    assert ingestor._deployment_info_cache[deployment_id] == deployment

    # make sure that we've started a new subscription for the deployment info stream key
    assert ingestor.redis.any_stream_is_registered(
        MessageEndpoints.atlas_deployment_info(deployment_name=deployment_id),
        ingestor._handle_deployment_info_update,
    )

    ingestor.signal_manager.process.assert_called_once_with(msg, deployment)


def test_handle_message_after_deployment_info_update(ingestor):
    """A deployment update replaces cached info used to dispatch subsequent messages."""
    deployment = _deployment_info_message()
    deployment_id = deployment.deployment_id
    msg = messages.MessagingServiceMessage(
        service_name="signal",
        message=[messages.MessagingServiceTextContent(content="Hello, Signal!")],
        scope=["user1", "user2"],
    )
    ingestor._handle_deployment_info_update(
        {"data": deployment}, parent=ingestor, deployment_id=deployment_id
    )
    updated_deployment = deployment.model_copy(deep=True)
    updated_deployment.name = "Updated Deployment"
    updated_deployment.messaging_services[0].group_id = "updated_signal_group"
    ingestor._handle_deployment_info_update(
        {"data": updated_deployment}, parent=ingestor, deployment_id=deployment_id
    )

    ingestor.handle_message({"data": msg}, ingestor.get_stream_key(deployment_id).endpoint)

    assert ingestor._deployment_info_cache[deployment_id] == updated_deployment
    ingestor.signal_manager.process.assert_called_once_with(msg, updated_deployment)
