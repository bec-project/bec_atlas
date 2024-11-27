from __future__ import annotations

import os
import threading

from bec_lib import messages
from bec_lib.logger import bec_logger
from bec_lib.serialization import MsgpackSerialization
from redis import Redis
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
        self.redis = Redis(host=redis_host, port=redis_port)

        self.shutdown_event = threading.Event()
        self.available_deployments = {}
        self.deployment_listener_thread = None
        self.receiver_thread = None
        self.consumer_name = f"ingestor_{os.getpid()}"
        self.create_consumer_group()
        self.start_deployment_listener()
        self.start_receiver()

    def create_consumer_group(self):
        """
        Create the consumer group for the ingestor.

        """
        try:
            self.redis.xgroup_create(
                name="internal/database_ingest", groupname="ingestor", mkstream=True
            )
        except ResponseError as exc:
            if "BUSYGROUP Consumer Group name already exists" in str(exc):
                logger.info("Consumer group already exists.")
            else:
                raise exc

    def start_deployment_listener(self):
        """
        Start the listener for the available deployments.

        """
        out = self.redis.get("deployments")
        if out:
            self.available_deployments = out
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

    def update_available_deployments(self):
        """
        Update the available deployments from the Redis queue.
        """
        sub = self.redis.pubsub()
        sub.subscribe("deployments")
        while not self.shutdown_event.is_set():
            out = sub.get_message(ignore_subscribe_messages=True, timeout=1)
            if out:
                logger.info(f"Updating available deployments: {out}")
                self.available_deployments = out
        sub.close()

    def ingestor_loop(self):
        """
        The main loop for the ingestor.

        """
        while not self.shutdown_event.is_set():
            data = self.redis.xreadgroup(
                groupname="ingestor",
                consumername=self.consumer_name,
                streams={"internal/database_ingest": ">"},
                block=1000,
            )

            if not data:
                logger.debug("No messages to ingest.")
                continue

            for stream, msgs in data:
                for message in msgs:
                    msg_dict = MsgpackSerialization.loads(message[1])
                    self.handle_message(msg_dict)
                    self.redis.xack(stream, "ingestor", message[0])

    def handle_message(self, msg_dict: dict):
        """
        Handle a message from the Redis queue.

        Args:
            msg_dict (dict): The message dictionary.
            parent (DataIngestor): The parent object.

        """
        data = msg_dict.get("data")
        if data is None:
            return
        deployment = msg_dict.get("deployment")
        if deployment is None:
            return

        if not deployment == self.available_deployments.get(deployment):
            return

        if isinstance(data, messages.ScanStatusMessage):
            self.update_scan_status(data)

    def update_scan_status(self, msg: messages.ScanStatusMessage):
        """
        Update the status of a scan in the database. If the scan does not exist, create it.

        Args:
            msg (messages.ScanStatusMessage): The message containing the scan status.

        """
        if not hasattr(msg, "session_id"):
            # TODO for compatibility with the old message format; remove once the bec_lib is updated
            session_id = msg.info.get("session_id")
        else:
            session_id = msg.session_id
        if not session_id:
            return
        # scans are indexed by the scan_id, hence we can use find_one and search by the ObjectId
        data = self.datasource.db["scans"].find_one({"_id": msg.scan_id})
        if data is None:
            msg_conv = ScanStatus(
                owner_groups=["admin"], access_groups=["admin"], **msg.model_dump()
            )
            msg_conv._id = msg_conv.scan_id

            # TODO for compatibility with the old message format; remove once the bec_lib is updated
            out = msg_conv.__dict__
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
        self.datasource.shutdown()
