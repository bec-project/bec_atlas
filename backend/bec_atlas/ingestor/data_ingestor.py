from __future__ import annotations

import os
import threading
from functools import lru_cache

from bec_lib import messages
from bec_lib.logger import bec_logger
from bec_lib.redis_connector import RedisConnector
from bec_lib.serialization import MsgpackSerialization
from bson import ObjectId
from redis.exceptions import ResponseError

from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import ScanStatus, Session

logger = bec_logger.logger


class DataIngestor:

    def __init__(self, config: dict) -> None:
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
                try:
                    self.handle_message(out, deployment_id)
                except Exception as e:
                    logger.error(f"Error handling message from {stream}: {e}")
                self.redis._redis_conn.xack(stream, "ingestor", message[0])

    def handle_message(self, msg_dict: dict, deployment_id: str):
        """
        Handle a message from the Redis queue.

        Args:
            msg_dict (dict): The message dictionary.
            deployment_id (str): The deployment id

        """
        for key, val in msg_dict.items():
            match key:
                case "scan_status":
                    if not isinstance(val, messages.ScanStatusMessage):
                        logger.error("Invalid scan_status message format.")
                        continue
                    self.update_scan_status(val, deployment_id)
                case "scan_history":
                    if not isinstance(val, messages.ScanHistoryMessage):
                        logger.error("Invalid scan_history message format.")
                        continue
                    self.update_scan_history(val, deployment_id)
                case "account":
                    if not isinstance(val, messages.VariableMessage):
                        logger.error("Invalid account message format.")
                        continue
                    self.update_account(val, deployment_id)
                case _:
                    logger.warning(f"Unknown message type: {key}")

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

    def update_scan_status(self, msg: messages.ScanStatusMessage, deployment_id: str):
        """
        Update the status of a scan in the database. If the scan does not exist, create it.

        Args:
            msg (messages.ScanStatusMessage): The message containing the scan status.
            deployment_id (str): The deployment id

        """
        session_id = msg.session_id
        if not session_id:
            session_id = "_default_"

        if session_id == "_default_":
            session = self.get_default_session(deployment_id)
        else:
            session = self.datasource.db["sessions"].find_one({"_id": ObjectId(session_id)})

        if session is None:
            logger.error(f"Session {session_id} not found.")
            return

        session = Session(**session)

        # scans are indexed by the scan_id, hence we can use find_one and search by the ObjectId
        data = self.datasource.db["scans"].find_one({"_id": msg.scan_id})
        if data is None:
            msg_conv = ScanStatus(
                owner_groups=["admin"], access_groups=session.access_groups, **msg.model_dump()
            )
            msg_conv.session_id = str(session.id)

            out = msg_conv.model_dump(exclude_none=True)
            out["_id"] = msg.scan_id

            self.datasource.db["scans"].insert_one(out)
        else:
            self.datasource.db["scans"].update_one(
                {"_id": msg.scan_id}, {"$set": {"status": msg.status}}
            )

    def update_scan_history(self, msg: messages.ScanHistoryMessage, deployment_id: str):
        """
        Update the history of a scan in the database. If the scan does not exist, skip it.

        Args:
            msg (messages.ScanHistoryMessage): The message containing the scan history.
            deployment_id (str): The deployment id

        """
        data = self.datasource.db["scans"].find_one({"_id": msg.scan_id})
        if data is None:
            logger.error(f"Scan {msg.scan_id} not found.")
            return

        data_to_set = {
            "start_time": msg.start_time,
            "end_time": msg.end_time,
            "file_path": msg.file_path,
        }

        self.datasource.db["scans"].update_one({"_id": msg.scan_id}, {"$set": data_to_set})

    def update_account(self, msg: messages.VariableMessage, deployment_id: str):
        """
        Update the account information in the database.
        If the account (i.e. pgroup) matches an existing experiment, set the active_session_id
        of the deployment to the session id of the experiment.

        Args:
            msg (messages.VariableMessage): The message containing the account information.
            deployment_id (str): The deployment id

        """
        data = self.datasource.db["deployments"].find_one({"_id": ObjectId(deployment_id)})
        if data is None:
            logger.error(f"Deployment {deployment_id} not found.")
            return

        deployment = data

        experiment = self.datasource.db["experiments"].find_one({"_id": msg.value})

        if experiment is None:
            logger.info(
                f"No experiment found for pgroup {msg.value}. Setting active_session_id to the default."
            )
            default_session = self.get_default_session(deployment_id)
            if default_session:
                self.datasource.db["deployments"].update_one(
                    {"_id": ObjectId(deployment_id)},
                    {"$set": {"active_session_id": str(default_session["_id"])}},
                )
            else:
                self.datasource.db["deployments"].update_one(
                    {"_id": ObjectId(deployment_id)},
                    {"$set": {"active_session_id": None}},  # No default session found
                )
            return

        # Find the latest session for the experiment and deployment
        session = self.datasource.db["sessions"].find_one(
            {"experiment_id": experiment["_id"], "deployment_id": str(deployment["_id"])}
        )
        if session is None:
            logger.info(f"No session found for experiment {experiment['_id']}, creating a new one.")
            new_session = Session(
                name=msg.value,
                experiment_id=str(experiment["_id"]),
                deployment_id=str(deployment["_id"]),
                owner_groups=experiment.get("access_groups", []) + ["admin"],
                access_groups=experiment.get("access_groups", []) + [msg.value],
            )
            session_id = str(
                self.datasource.db["sessions"].insert_one(new_session.model_dump()).inserted_id
            )
        else:
            session_id = str(session["_id"])
        logger.info(
            f"Setting active_session_id for deployment {deployment_id} to {session_id} (experiment {experiment['_id']})"
        )

        self.datasource.db["deployments"].update_one(
            {"_id": ObjectId(deployment_id)}, {"$set": {"active_session_id": session_id}}
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

    bec_logger.level = bec_logger.LOGLEVEL.INFO

    ingestor = DataIngestor(config=CONFIG)
    event = threading.Event()
    while not event.is_set():
        try:
            event.wait(1)
        except KeyboardInterrupt:
            event.set()
    ingestor.shutdown()


if __name__ == "__main__":
    main()
