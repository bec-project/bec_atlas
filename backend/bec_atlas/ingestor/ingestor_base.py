from __future__ import annotations

import os
import threading
from abc import ABC, abstractmethod
from functools import lru_cache
from string import Template

from bec_lib.logger import bec_logger
from bec_lib.redis_connector import RedisConnector
from bec_lib.serialization import MsgpackSerialization
from redis.exceptions import ResponseError

from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource

logger = bec_logger.logger


class IngestorBase(ABC):
    STREAM_KEY_TEMPLATE = Template("internal/deployment/${deployment_id}/ingest")

    def __init__(self, config: dict):
        self.config = config
        self.datasource = MongoDBDatasource(config=self.config["mongodb"])
        self.datasource.connect(include_setup=False)

        redis_host = config.get("redis", {}).get("host", "localhost")
        redis_port = config.get("redis", {}).get("port", 6380)

        if config.get("redis", {}).get("sync_instance"):
            self.redis = config.get("redis", {}).get("sync_instance")
        else:
            self.redis = RedisConnector(
                f"{redis_host}:{redis_port}"  # username="ingestor", password="ingestor"
            )
        username = config.get("redis", {}).get("username", "ingestor")
        password = config.get("redis", {}).get("password")
        self.redis.authenticate(password=password, username=username)
        self.redis.set_retry_enabled(True)

        self.shutdown_event = threading.Event()
        self.available_deployments = []
        self.deployment_listener_thread = None
        self.receiver_thread = None
        self.reclaim_pending_messages_thread = None
        self.consumer_name = f"ingestor_{os.getpid()}"
        self.start_deployment_listener()
        self.start_receiver()
        logger.success("Data ingestor started.")

    def start_deployment_listener(self):
        """
        Start the listener for the available deployments.

        """
        out = self.redis.get("deployments")
        if out:
            self.available_deployments = out.data
            self.update_consumer_groups()
        self.deployment_listener_thread = threading.Thread(
            target=self.update_available_deployments, name="deployment_listener"
        )
        self.deployment_listener_thread.start()

    def start_receiver(self):
        """
        Start the receiver for the Redis queue.

        """
        self.receiver_thread = threading.Thread(target=self.ingestor_loop, name="receiver")
        self.receiver_thread.start()
        self.reclaim_pending_messages_thread = threading.Thread(
            target=self.reclaim_pending_messages, name="reclaim_pending_messages"
        )
        self.reclaim_pending_messages_thread.start()

    def update_available_deployments(self):
        """
        Update the available deployments from the Redis queue.
        """

        def _update_deployments(data, parent):
            parent.available_deployments = data
            parent.update_consumer_groups()

        self.redis.register("deployments", cb=_update_deployments, parent=self)

    def update_consumer_groups(self):
        """
        Update the consumer groups for the available deployments.

        """
        for deployment in self.available_deployments:
            try:
                self.redis._redis_conn.xgroup_create(
                    name=self.STREAM_KEY_TEMPLATE.substitute(deployment_id=deployment["id"]),
                    groupname="ingestor",
                    mkstream=True,
                )
            except ResponseError as exc:
                if "BUSYGROUP Consumer Group name already exists" in str(exc):
                    continue
                raise exc

    def reclaim_pending_messages(self):
        """
        Reclaim any pending messages from the Redis queue.

        """
        while not self.shutdown_event.is_set():
            to_process = []
            for deployment in self.available_deployments:
                pending_messages = self.redis._redis_conn.xautoclaim(
                    self.STREAM_KEY_TEMPLATE.substitute(deployment_id=deployment["id"]),
                    "ingestor",
                    self.consumer_name,
                    min_idle_time=1000,
                )
                if pending_messages[1]:
                    to_process.append(
                        [
                            self.STREAM_KEY_TEMPLATE.substitute(
                                deployment_id=deployment["id"]
                            ).encode(),
                            pending_messages[1],
                        ]
                    )

            if to_process:
                self._handle_stream_messages(to_process)
            self.shutdown_event.wait(10)

    def ingestor_loop(self):
        """
        The main loop for the ingestor.

        """
        while not self.shutdown_event.is_set():
            if not self.available_deployments:
                self.shutdown_event.wait(1)
                continue
            streams = {
                self.STREAM_KEY_TEMPLATE.substitute(deployment_id=deployment["id"]): ">"
                for deployment in self.available_deployments
            }
            data = self.redis._redis_conn.xreadgroup(
                groupname="ingestor", consumername=self.consumer_name, streams=streams, block=1000
            )

            if not data:
                logger.debug("No messages to ingest.")
                continue

            self._handle_stream_messages(data)

    def _handle_stream_messages(self, data):
        for stream, msgs in data:
            for message in msgs:
                msg = message[1]
                out = {}
                for key, val in msg.items():
                    out[key.decode()] = MsgpackSerialization.loads(val)
                deployment_id = stream.decode().split("/")[-2]
                self.handle_message(out, deployment_id)
                self.redis._redis_conn.xack(stream, "ingestor", message[0])

    @abstractmethod
    def handle_message(self, msg_dict: dict, deployment_id: str):
        """
        Handle a single message from the Redis queue.

        Args:
            msg_dict (dict): The message dictionary.
            deployment_id (str): The deployment ID.

        """

    @lru_cache()
    def get_default_session(self, deployment_id: str):
        """
        Get the session id for a deployment.

        Args:
            deployment_id (str): The deployment id

        Returns:
            str: The session id

        """
        out = self.datasource.db["sessions"].find_one(
            {"name": "_default_", "deployment_id": deployment_id}
        )
        return out

    def shutdown(self):
        self.shutdown_event.set()
        if self.deployment_listener_thread:
            self.deployment_listener_thread.join()
        if self.receiver_thread:
            self.receiver_thread.join()
        if self.reclaim_pending_messages_thread:
            self.reclaim_pending_messages_thread.join()
        self.redis.shutdown()
        self.datasource.shutdown()
