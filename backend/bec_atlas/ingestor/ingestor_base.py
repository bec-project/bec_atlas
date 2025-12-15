from __future__ import annotations

import logging
import os
import threading
from abc import ABC, abstractmethod
from functools import lru_cache

from bec_lib.endpoints import EndpointInfo
from bec_lib.redis_connector import RedisConnector
from bec_lib.serialization import MsgpackSerialization
from bson import ObjectId
from redis.exceptions import ResponseError

from bec_atlas.datasources.endpoints import RedisAtlasEndpoints
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.datasources.redis_datasource import RedisDatasource
from bec_atlas.model import Deployments

logger = logging.getLogger(__name__)


class IngestorBase(ABC):

    def __init__(self, config: dict):
        self.config = config
        self.datasource = MongoDBDatasource(config=self.config["mongodb"])
        self.datasource.connect(include_setup=False)

        self.redis_datasource = RedisDatasource(config=self.config["redis"])
        self.redis: RedisConnector = self.redis_datasource.connector  # type: ignore

        self.shutdown_event = threading.Event()
        self.available_deployments = []
        self.deployment_listener_thread = None
        self.receiver_thread = None
        self.reclaim_pending_messages_thread = None
        self.consumer_name = f"ingestor_{os.getpid()}"
        self.start_deployment_listener()
        self.start_receiver()

    def start_deployment_listener(self):
        """
        Start the listener for the available deployments.

        """
        out = self.redis.get(RedisAtlasEndpoints.deployments())
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
                    name=self.get_stream_key(deployment["id"]).endpoint,
                    groupname="ingestor",
                    mkstream=True,
                )
            except ResponseError as exc:
                if "BUSYGROUP Consumer Group name already exists" in str(exc):
                    continue
                raise exc

    @abstractmethod
    def get_stream_key(self, deployment_id: str) -> EndpointInfo:
        """
        Get the stream key for the deployment.

        Args:
            deployment_id (str): The deployment id
        Returns:
            EndpointInfo: The endpoint info for the stream key
        """

    def reclaim_pending_messages(self):
        """
        Reclaim any pending messages from the Redis queue.

        """
        while not self.shutdown_event.is_set():
            to_process = []
            for deployment in self.available_deployments:
                try:
                    pending_messages = self.redis._redis_conn.xautoclaim(
                        self.get_stream_key(deployment["id"]).endpoint,
                        "ingestor",
                        self.consumer_name,
                        min_idle_time=10000,
                    )
                except ResponseError as exc:
                    if "NOGROUP No such key" in str(exc):
                        self.update_consumer_groups()
                        continue
                    logger.error(
                        f"Error reclaiming pending messages for deployment {deployment['id']}: {exc}"
                    )
                    continue
                if pending_messages[1]:
                    to_process.append(
                        [
                            self.get_stream_key(deployment["id"]).endpoint.encode(),
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
            try:
                streams = {
                    self.get_stream_key(deployment["id"]).endpoint: ">"
                    for deployment in self.available_deployments
                }
                data = self.redis._redis_conn.xreadgroup(
                    groupname="ingestor",
                    consumername=self.consumer_name,
                    streams=streams,
                    block=1000,
                )

                if not data:
                    logger.debug("No messages to ingest.")
                    continue

                self._handle_stream_messages(data)
            except Exception as exc:
                logger.error(f"Error in ingestor loop: {exc}")

    def _handle_stream_messages(self, data):
        for stream, msgs in data:
            for message in msgs:
                msg = message[1]
                out = {}
                for key, val in msg.items():
                    out[key.decode()] = MsgpackSerialization.loads(val)
                self.handle_message(out, stream.decode())
                self.redis._redis_conn.xack(stream, "ingestor", message[0])
                self.redis._redis_conn.xdel(stream, message[0])

    @abstractmethod
    def handle_message(self, msg_dict: dict, stream_key: str):
        """
        Handle a single message from the Redis queue.

        Args:
            msg_dict (dict): The message dictionary.
            stream_key (str): The stream key.

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
            {"name": "_default_", "deployment_id": ObjectId(deployment_id)}
        )
        return out

    def broadcast_deployment_update(self, deployment_id: str | ObjectId):
        """
        Broadcast a deployment update to the Redis queue.

        Args:
            deployment_id (str | ObjectId): The deployment id

        """
        if isinstance(deployment_id, ObjectId):
            deployment_id = str(deployment_id)
        deployments = self.datasource.get_full_deployment(filter={"_id": deployment_id})
        deployment_info = next(iter(deployments), None)
        if deployment_info:
            self.redis_datasource.update_deployment_info(deployment_info)

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
