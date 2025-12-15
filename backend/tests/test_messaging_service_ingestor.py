import time
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
        ingestor = MessageServiceIngestor(config=app.config)
        MockSignalManager.assert_called_once_with(ingestor, app.config.get("signal", {}))
        yield ingestor
        ingestor.shutdown()


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
    assert ingestor.signal_manager.process.called_once_with(msg, deployment)


def test_handle_message(ingestor):
    """
    Test that the handle_message method updates deployment subscriptions and processes messages correctly.
    To this end, we will use fakeredis to post a new message to the stream key and trigger the entire flow
    of the handle_message method.
    """
    deployment_id = "678aa8d4875568640bd92176"
    msg = messages.MessagingServiceMessage(
        service_name="signal",
        message=[messages.MessagingServiceTextContent(content="Hello, Signal!")],
        scope=["user1", "user2"],
    )
    ingestor.redis.xadd(
        MessageEndpoints.atlas_deployment_info(deployment_name=deployment_id),
        {"data": _deployment_info_message()},
    )
    ingestor.redis.xadd(ingestor.get_stream_key(deployment_id), {"data": msg})
    time.sleep(1)  # Wait for the ingestor loop to process the message

    assert deployment_id in ingestor._deployment_info_cache

    # make sure that we've started a new subscription for the deployment info stream key
    assert (
        MessageEndpoints.atlas_deployment_info(deployment_name=deployment_id).endpoint
        in ingestor.redis._stream_topics_subscription
    )

    assert ingestor.signal_manager.process.called_once_with(
        msg, ingestor._deployment_info_cache[deployment_id]
    )


def test_handle_message_after_deployment_info_update(ingestor):
    """
    Test that the handle_message method processes messages correctly after a deployment info update. This is to ensure that we correctly update the deployment info cache and use the updated info to process messages.
    """
    deployment_id = "678aa8d4875568640bd92176"
    msg = messages.MessagingServiceMessage(
        service_name="signal",
        message=[messages.MessagingServiceTextContent(content="Hello, Signal!")],
        scope=["user1", "user2"],
    )
    ingestor.redis.xadd(
        MessageEndpoints.atlas_deployment_info(deployment_name=deployment_id),
        {"data": _deployment_info_message()},
    )
    ingestor.redis.xadd(ingestor.get_stream_key(deployment_id), {"data": msg})
    time.sleep(1)  # Wait for the ingestor loop to process the message
    ingestor._update_deployment_subscriptions(deployment_id)
    assert deployment_id in ingestor._deployment_info_cache

    time.sleep(1)  # Wait for the ingestor loop to process the message
    assert ingestor.signal_manager.process.called_once_with(
        msg, ingestor._deployment_info_cache[deployment_id]
    )
