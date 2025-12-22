from __future__ import annotations

import threading
from typing import Literal

from bec_lib import messages
from bec_lib.endpoints import EndpointInfo, MessageEndpoints
from bec_lib.logger import bec_logger

from bec_atlas.ingestor.ingestor_base import IngestorBase

logger = bec_logger.logger


class MessageServiceIngestor(IngestorBase):

    def get_stream_key(self, deployment_id: str) -> EndpointInfo:
        return MessageEndpoints.message_service_ingest(deployment_name=deployment_id)

    def handle_message(
        self, msg_dict: dict[Literal["data"], messages.MessagingServiceMessage], deployment_id: str
    ):
        """
        Handle a message from the Redis queue.

        Args:
            msg_dict (dict): The message dictionary.
            deployment_id (str): The deployment id

        """
        msg = msg_dict.get("data")
        if not msg:
            logger.warning("No data found in message.")
            return

        if self.message_scope_is_valid(msg, deployment_id):
            self.process_message(msg)
        else:
            logger.warning(f"Message scope is not valid for deployment {deployment_id}.")

    def message_scope_is_valid(
        self, msg: messages.MessagingServiceMessage, deployment_id: str
    ) -> bool:
        """
        Check if the message scope is valid for the given deployment.

        Args:
            msg (messages.MessagingServiceMessage): The message.
            deployment_id (str): The deployment id
        Returns:
            bool: True if the message scope is valid, False otherwise.

        """
        # For now, we assume all messages are valid.
        return True

    def process_message(self, msg: messages.MessagingServiceMessage):
        """
        Process the messaging service message.

        Args:
            msg (messages.MessagingServiceMessage): The message.

        """
        match msg.service_name:
            case "signal":
                self.process_signal_message(msg)
            case "teams":
                self.process_teams_message(msg)
            case "scilog":
                self.process_scilog_message(msg)
            case _:
                logger.error(f"Unknown messaging service: {msg.service_name}")

    def process_signal_message(self, msg: messages.MessagingServiceMessage):
        """
        Process a Signal message.

        Args:
            msg (messages.MessagingServiceMessage): The message.

        """
        pass

    def process_teams_message(self, msg: messages.MessagingServiceMessage):
        """
        Process a Teams message.
        Args:
            msg (messages.MessagingServiceMessage): The message.

        """
        pass

    def process_scilog_message(self, msg: messages.MessagingServiceMessage):
        """
        Process a SciLog message.

        Args:
            msg (messages.MessagingServiceMessage): The message.

        """
        pass


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
