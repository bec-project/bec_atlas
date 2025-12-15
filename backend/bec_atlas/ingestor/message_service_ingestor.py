from __future__ import annotations

import threading
from typing import Literal

from bec_lib import messages
from bec_lib.endpoints import EndpointInfo, MessageEndpoints
from bec_lib.logger import bec_logger

from bec_atlas.ingestor.ingestor_base import IngestorBase
from bec_atlas.ingestor.scilog_logbook_manager import SciLogLogbookManager
from bec_atlas.ingestor.signal_manager import SignalManager

logger = bec_logger.logger


class MessageServiceIngestor(IngestorBase):

    def __init__(self, config: dict):
        super().__init__(config=config)
        self.signal_manager = SignalManager(self, config.get("signal", {}))
        self.scilog_manager = SciLogLogbookManager(config.get("scilog", {}))
        self._deployment_info_cache: dict[str, messages.DeploymentInfoMessage] = {}
        logger.success("Message service ingestor started.")

    def get_stream_key(self, deployment_id: str) -> EndpointInfo:
        return MessageEndpoints.message_service_ingest(deployment_name=deployment_id)

    def handle_message(
        self, msg_dict: dict[Literal["data"], messages.MessagingServiceMessage], stream_key: str
    ):
        """
        Handle a message from the Redis queue.

        Args:
            msg_dict (dict): The message dictionary.
            stream_key (str): The stream key.

        """

        deployment_id = stream_key.split("/")[-3]
        self._update_deployment_subscriptions(deployment_id)

        msg = msg_dict.get("data")
        if not msg:
            logger.warning("No data found in message.")
            return

        deployment_info = self._deployment_info_cache.get(deployment_id)
        if not deployment_info:
            logger.warning(f"No deployment info found for deployment {deployment_id}.")
            return

        if self.message_scope_is_valid(msg, deployment_info):
            self.process_message(msg, deployment_info)
        else:
            logger.warning(f"Message scope is not valid for deployment {deployment_id}.")

    def _update_deployment_subscriptions(self, deployment_id: str):
        """
        Check if we are already subscribed to the deployment info stream, and if not, subscribe to it.
        Args:
            deployment_id (str): The deployment id
        """
        if deployment_id in self._deployment_info_cache:
            return

        data = self.redis.xread(
            MessageEndpoints.atlas_deployment_info(deployment_name=deployment_id)
        )
        if data:
            self._deployment_info_cache[deployment_id] = data[-1]["data"]
        self.redis.register(
            MessageEndpoints.atlas_deployment_info(deployment_name=deployment_id),
            cb=self._handle_deployment_info_update,
            parent=self,
            deployment_id=deployment_id,
        )

    @staticmethod
    def _handle_deployment_info_update(
        msg: dict[str, messages.DeploymentInfoMessage],
        parent: MessageServiceIngestor,
        deployment_id: str,
    ):
        """
        Handle deployment info update messages.

        Args:
            msg (dict[str, messages.DeploymentInfoMessage]): The message dictionary.
            parent (MessageServiceIngestor): The parent ingestor instance.
            deployment_id (str): The deployment id.

        """
        if "data" not in msg:
            return
        data = msg["data"]
        parent._deployment_info_cache[deployment_id] = data

    def message_scope_is_valid(
        self, msg: messages.MessagingServiceMessage, deployment: messages.DeploymentInfoMessage
    ) -> bool:
        """
        Check if the message scope is valid for the given deployment.

        Args:
            msg (messages.MessagingServiceMessage): The message.
            deployment (messages.DeploymentInfoMessage): The deployment info message.
        Returns:
            bool: True if the message scope is valid, False otherwise.

        """
        # For now, we assume all messages are valid.
        # Later, we will fetch the info from redis and check the scopes.
        # message_service_config: MessageServiceConfig = deployment.messaging_services
        # service_info = next(
        #     (
        #         service
        #         for service in deployment.messaging_services
        #         if service.service_name == msg.service_name
        #     ),
        #     None,
        # )
        # if not service_info:
        #     return False
        # if not service_info.enabled:
        #     return False
        # if not service_info.scopes:
        #     return True  # No scopes means all scopes are allowed.
        # if not msg.scopes:
        #     return False  # Message has no scopes but service requires scopes.

        return True

    def process_message(
        self, msg: messages.MessagingServiceMessage, deployment: messages.DeploymentInfoMessage
    ):
        """
        Process the messaging service message.

        Args:
            msg (messages.MessagingServiceMessage): The message.
            deployment (messages.DeploymentInfoMessage): The deployment info message.

        """
        match msg.service_name:
            case "signal":
                self.signal_manager.process(msg, deployment)
            case "teams":
                pass  # not implemented yet
            case "scilog":
                self.scilog_manager.process(msg, deployment)
            case _:
                logger.error(f"Unknown messaging service: {msg.service_name}")

    def shutdown(self):
        self.signal_manager.shutdown()
        super().shutdown()


def main():  # pragma: no cover
    from bec_atlas.utils.env_loader import load_env

    bec_logger.level = bec_logger.LOGLEVEL.INFO

    config = load_env()
    ingestor = MessageServiceIngestor(config=config)
    event = threading.Event()
    while not event.is_set():
        try:
            event.wait(1)
        except KeyboardInterrupt:
            event.set()
    ingestor.shutdown()


if __name__ == "__main__":  # pragma: no cover
    main()
