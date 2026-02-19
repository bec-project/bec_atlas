from __future__ import annotations

import threading

from bec_lib import messages
from bec_lib.endpoints import EndpointInfo, MessageEndpoints
from bec_lib.logger import bec_logger
from bson import ObjectId

from bec_atlas.ingestor.ingestor_base import IngestorBase
from bec_atlas.ingestor.scilog_logbook_manager import SciLogLogbookManager
from bec_atlas.model.model import ScanStatus, Session

logger = bec_logger.logger


class DataIngestor(IngestorBase):
    def __init__(self, config: dict):
        super().__init__(config)
        self.scilog_manager = SciLogLogbookManager(config=config.get("scilog", {}))

    def get_stream_key(self, deployment_id: str) -> EndpointInfo:
        return MessageEndpoints.atlas_deployment_ingest(deployment_name=deployment_id)

    def handle_message(self, msg_dict: dict, stream_key: str):
        """
        Handle a message from the Redis queue.

        Args:
            msg_dict (dict): The message dictionary.
            stream_key (str): The stream key.

        """

        deployment_id = stream_key.split("/")[-2]
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
        if self.datasource is None or self.datasource.db is None:
            logger.error("Datasource not initialized.")
            return

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
        access_groups = session.access_groups + session.owner_groups
        if data is None:
            msg_conv = ScanStatus(
                owner_groups=["admin"], access_groups=access_groups, **msg.model_dump()
            )
            msg_conv.session_id = session.id

            out = msg_conv.model_dump(exclude_none=True)
            out["_id"] = msg.scan_id

            self.datasource.db["scans"].insert_one(out)
        else:
            self.datasource.db["scans"].update_one(
                {"_id": msg.scan_id}, {"$set": {"status": msg.status}}
            )

    def update_scan_history(self, msg: messages.ScanHistoryMessage, deployment_id: str):
        """
        Update a scan with a ScanHistoryMessage in the database. If the scan does not exist, skip it.

        Args:
            msg (messages.ScanHistoryMessage): The message containing the scan history.
            deployment_id (str): The deployment id

        """
        if self.datasource is None or self.datasource.db is None:
            logger.error("Datasource not initialized.")
            return

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
        if self.datasource is None or self.datasource.db is None:
            logger.error("Datasource not initialized.")
            return
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
                    {"$set": {"active_session_id": default_session["_id"]}},
                )
            else:
                self.datasource.db["deployments"].update_one(
                    {"_id": ObjectId(deployment_id)},
                    {"$set": {"active_session_id": None}},  # No default session found
                )
            return

        # Find the latest session for the experiment and deployment
        session = self.datasource.get_full_session(
            {"experiment_id": experiment["_id"], "deployment_id": deployment_id}
        )

        if not session:
            logger.info(f"No session found for experiment {experiment['_id']}, creating a new one.")
            session = Session(
                name=msg.value,
                experiment_id=str(experiment["_id"]),
                deployment_id=deployment["_id"],
                owner_groups=deployment.get("owner_groups", []),
                access_groups=[msg.value],
            )
            session_id = self.datasource.db["sessions"].insert_one(
                session.model_dump(exclude_none=False)
            )
            session = self.datasource.find_one("sessions", {"_id": session_id.inserted_id}, Session)

        else:
            session = session[0]  # Take the latest session
        if session is None:
            logger.error("Failed to create or retrieve session.")
            return

        if experiment is not None and not session.messaging_services:
            try:
                self._set_scilog_logbook_for_session(session)
            except Exception as e:
                logger.error(f"Failed to set SciLog logbook for session: {e}")

        logger.info(
            f"Setting active_session_id for deployment {deployment_id} to {session.id} (experiment {experiment['_id']})"
        )

        self.datasource.db["deployments"].update_one(
            {"_id": ObjectId(deployment_id)}, {"$set": {"active_session_id": session.id}}
        )

        if deployment is not None:
            deployments = self.datasource.get_full_deployment({"_id": deployment_id})
            if deployments:
                self.redis_datasource.update_deployment_info(deployment=deployments[0])

    def _set_scilog_logbook_for_session(self, session: Session):
        """
        Fetch the available SciLog logbooks from Redis. If a logbook's ownerGroup
        matches the session's experiment_id, create a SciLog messaging service for the session
        if one doesn't exist yet.

        Args:
            session (Session): The session object.

        """
        if self.datasource is None or self.datasource.db is None:
            logger.error("Datasource not initialized.")
            return

        if session.experiment_id is None:
            return

        out = self.scilog_manager.fetch_logbooks_for_pgroup(session.experiment_id)
        if not out:
            return
        target_logbook = out[0]  # Take the first logbook found

        if not target_logbook:
            return

        logger.info(
            f"Setting SciLog messaging service for session {session.id} with logbook {target_logbook['name']}"
        )

        # Create or update the messaging service document
        messaging_service_data = {
            "parent_id": session.id,
            "service_type": "scilog",
            "scope": "default",
            "enabled": True,
            "logbook_id": target_logbook.id,
            "name": target_logbook.name,
            "owner_groups": session.owner_groups,
            "access_groups": session.access_groups,
        }

        # We check if we already have a scilog messaging service with scope "default" for the session, if so, we skip the update.
        # If we don't have one, we create it.
        existing_service = self.datasource.db["messaging_services"].find_one(
            {"parent_id": session.id, "service_type": "scilog", "scope": "default"}
        )
        if existing_service:
            # Update the name of the logbook in case it has changed
            if existing_service.get("name") != target_logbook.name:
                self.datasource.db["messaging_services"].update_one(
                    {"_id": existing_service["_id"]}, {"$set": {"name": target_logbook.name}}
                )
            logger.info(
                f"SciLog messaging service already exists for session {session.id}, skipping creation."
            )
            return
        self.datasource.db["messaging_services"].insert_one(messaging_service_data)


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


if __name__ == "__main__":  # pragma: no cover
    main()
