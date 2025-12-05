from __future__ import annotations

import threading
from string import Template

from bec_lib import messages
from bec_lib.logger import bec_logger
from bson import ObjectId

from bec_atlas.ingestor.ingestor_base import IngestorBase
from bec_atlas.model.model import ScanStatus, Session

logger = bec_logger.logger


class DataIngestor(IngestorBase):
    STREAM_KEY_TEMPLATE = Template("internal/deployment/${deployment_id}/ingest")

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


def main():  # pragma: no cover
    from bec_atlas.utils.env_loader import load_env

    bec_logger.level = bec_logger.LOGLEVEL.INFO

    config = load_env()
    ingestor = DataIngestor(config=config)
    event = threading.Event()
    while not event.is_set():
        try:
            event.wait(1)
        except KeyboardInterrupt:
            event.set()
    ingestor.shutdown()


if __name__ == "__main__":
    main()
