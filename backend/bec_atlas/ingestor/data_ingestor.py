from __future__ import annotations

import json
import os
import threading
from functools import lru_cache

from bec_lib import messages
from bec_lib.logger import bec_logger
from bec_lib.redis_connector import RedisConnector
from bec_lib.serialization import MsgpackSerialization

# from redis import Redis
from bson import ObjectId
from redis.exceptions import ResponseError

from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import ScanStatus

logger = bec_logger.logger


class DataIngestor:

    def __init__(self, config: dict) -> None:
        self.config = config
        self.datasource = MongoDBDatasource(config=self.config["mongodb"])
        self.datasource.connect(include_setup=False)

        redis_host = config.get("redis", {}).get("host", "localhost")
        redis_port = config.get("redis", {}).get("port", 6380)
        self.redis = RedisConnector(
            f"{redis_host}:{redis_port}"  # username="ingestor", password="ingestor"
        )
        # self.redis.authenticate(
        #     config.get("redis", {}).get("password", "ingestor"), username="ingestor"
        # )

        self.redis._redis_conn.connection_pool.connection_kwargs["username"] = "ingestor"
        self.redis._redis_conn.connection_pool.connection_kwargs["password"] = "ingestor"

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
        out = self.redis.get("deployments")
        if out:
            self.available_deployments = json.loads(out)
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
                    name=f"internal/deployment/{deployment['id']}/ingest",
                    groupname="ingestor",
                    mkstream=True,
                )
            except ResponseError as exc:
                if "BUSYGROUP Consumer Group name already exists" in str(exc):
                    logger.info("Consumer group already exists.")
                else:
                    raise exc

    def reclaim_pending_messages(self):
        """
        Reclaim any pending messages from the Redis queue.

        """
        while not self.shutdown_event.is_set():
            to_process = []
            for deployment in self.available_deployments:
                pending_messages = self.redis._redis_conn.xautoclaim(
                    f"internal/deployment/{deployment['id']}/ingest",
                    "ingestor",
                    self.consumer_name,
                    min_idle_time=1000,
                )
                if pending_messages[1]:
                    to_process.append(
                        [
                            f"internal/deployment/{deployment['id']}/ingest".encode(),
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
                f"internal/deployment/{deployment['id']}/ingest": ">"
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

    def handle_message(self, msg_dict: dict, deploymend_id: str):
        """
        Handle a message from the Redis queue.

        Args:
            msg_dict (dict): The message dictionary.
            parent (DataIngestor): The parent object.

        """
        data = msg_dict.get("data")
        if data is None:
            return

        if isinstance(data, messages.ScanStatusMessage):
            self.update_scan_status(data, deploymend_id)

    @lru_cache()
    def get_default_session_id(self, deployment_id: str):
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
        if out is None:
            return None
        return out["_id"]

    def update_scan_status(self, msg: messages.ScanStatusMessage, deployment_id: str):
        """
        Update the status of a scan in the database. If the scan does not exist, create it.

        Args:
            msg (messages.ScanStatusMessage): The message containing the scan status.
            deployment_id (str): The deployment id

        """
        if not hasattr(msg, "session_id"):
            # TODO for compatibility with the old message format; remove once the bec_lib is updated
            session_id = msg.info.get("session_id")
        else:
            session_id = msg.session_id
        if not session_id:
            session_id = "_default_"

        if session_id == "_default_":
            session_id = self.get_default_session_id(deployment_id)
            if session_id is None:
                logger.error("Default session not found.")
                return

        # scans are indexed by the scan_id, hence we can use find_one and search by the ObjectId
        data = self.datasource.db["scans"].find_one({"_id": msg.scan_id})
        if data is None:
            msg_conv = ScanStatus(
                owner_groups=["admin"], access_groups=["admin"], **msg.model_dump()
            )

            out = msg_conv.model_dump(exclude_none=True)
            out["_id"] = msg.scan_id

            # TODO for compatibility with the old message format; remove once the bec_lib is updated
            out["session_id"] = session_id

            self.datasource.db["scans"].insert_one(out)
        else:
            self.datasource.db["scans"].update_one(
                {"_id": msg.scan_id}, {"$set": {"status": msg.status}}
            )

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


def main():  # pragma: no cover
    from bec_atlas.main import CONFIG

    ingestor = DataIngestor(config=CONFIG)
    event = threading.Event()
    while not event.is_set():
        try:
            event.wait(1)
        except KeyboardInterrupt:
            event.set()
    ingestor.shutdown()


if __name__ == "__main__":
    bec_logger.level = bec_logger.LOGLEVEL.INFO
    main()
