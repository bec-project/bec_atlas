"""
A module for fetching all available logbooks from SciLog and storing them in redis for
quick access.
"""

from __future__ import annotations

import functools
import logging
import os
import uuid
from functools import wraps

import requests
import scilog
from bec_lib import messages
from scilog import models as scilog_models

logger = logging.getLogger(__name__)


def reauthenticate(func):
    """
    A decorator to re-authenticate the SciLogLogbookManager if the token has expired.

    Args:
        func: The function to decorate.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except requests.HTTPError as exc:
            self.scilog.core.http_client.reset_token()
            print(f"HTTP error occurred: {exc}")
            return func(self, *args, **kwargs)

    return wrapper


class SciLogLogbookManager:
    scilog_base_url = "https://scilog.psi.ch/api/v1"

    def __init__(
        self, config: dict | None = None, token: str | None = None, temp_dir: str | None = None
    ):
        if not token and not config:
            raise ValueError("Either token or config must be provided.")
        self.token = token
        self.temp_dir = temp_dir or "/tmp/scilog_logbook_manager"
        self.config = config
        self.scilog = scilog.SciLog(
            address=self.scilog_base_url,
            options={
                "username": config["username"] if config else None,
                "password": config["password"] if config else None,
                "auto_save_token": False,
            },
        )

    @reauthenticate
    def fetch_logbooks_for_pgroup(self, pgroup: str) -> list[scilog_models.Logbook]:
        """
        Fetch all logbooks for a given proposal group.

        Args:
            pgroup (str): The proposal group.
        Returns:
            list[scilog_models.Logbook]: A list of logbooks for the given proposal group.
        """

        logbooks = self.scilog.get_logbooks(where={"updateACL": {"in": [pgroup]}})
        return logbooks

    def process(
        self, msg: messages.MessagingServiceMessage, deployment: messages.DeploymentInfoMessage
    ):
        """
        Process a message for the SciLogLogbookManager.
        We use the deployment info to verify that the message is not exceeding the scope of what is allowed for the deployment.

        Args:
            msg (MessagingServiceMessage): The message to process.
            deployment (DeploymentInfoMessage): The deployment info message associated with the message.
        """

        logbook_ids = self.get_logbook_id(msg, deployment)
        if not logbook_ids:
            logger.warning(
                f"Message with scope {msg.scope} is not within the scope of the deployment {deployment.deployment_id}."
            )
            return
        for logbook_id in logbook_ids:
            self.ingest_data(msg, logbook_id)

    def get_logbook_id(
        self, msg: messages.MessagingServiceMessage, deployment: messages.DeploymentInfoMessage
    ) -> list[str] | None:
        """
        Get the logbook ID from the message if it is within the scope of the deployment.

        Args:
            msg (MessagingServiceMessage): The message to check.
            deployment (DeploymentInfoMessage): The deployment info message associated with the message.
        Returns:
            list[str] | None: The logbook IDs if the message scope is valid, None otherwise.
        """
        target_scope = msg.scope
        if not target_scope:
            return None
        if isinstance(target_scope, str):
            target_scope = [target_scope]

        logbook_ids = {}
        for service in deployment.messaging_services:
            if not service.service_type == "scilog" or not service.enabled:
                continue
            if not isinstance(service, messages.SciLogServiceInfo):
                continue
            logbook_ids[service.scope] = service.logbook_id

        if deployment.active_session:
            for service in deployment.active_session.messaging_services:
                if not service.service_type == "scilog" or not service.enabled:
                    continue
                if not isinstance(service, messages.SciLogServiceInfo):
                    continue
                logbook_ids[service.scope] = service.logbook_id

        confirmed_logbook_ids = [
            logbook_ids[scope] for scope in target_scope if scope in logbook_ids
        ]
        return confirmed_logbook_ids if confirmed_logbook_ids else None

    @functools.lru_cache(maxsize=128)
    def fetch_logbook_by_id(self, logbook_id: str) -> scilog_models.Logbook | None:
        """
        Fetch a logbook by its ID.

        Args:
            logbook_id (str): The ID of the logbook to fetch.
        Returns:
            scilog_models.Logbook | None: The logbook data if found, None otherwise.
        """

        @reauthenticate
        def inner_fetch(self):
            logbooks = self.scilog.get_logbooks(where={"id": logbook_id})
            if logbooks:
                return logbooks[0]
            if not logbooks:
                # Remove from cache if not found to avoid caching non-existence
                self.fetch_logbook_by_id.cache_clear()
            return None

        return inner_fetch(self)

    def ingest_data(self, msg: messages.MessagingServiceMessage, logbook_id: str):
        """
        Ingest data into the logbook.

        Args:
            msg (MessagingServiceMessage): The message containing the data to ingest.
            logbook_id (str): The ID of the logbook to ingest the data into.
        """
        # select logbook
        logbook = self.fetch_logbook_by_id(logbook_id)
        if not logbook:
            logger.error(f"Logbook with ID {logbook_id} not found.")
            return
        self.scilog.select_logbook(logbook)
        scilog_msg = self.scilog.new()
        files = []
        tmp_dir = None
        for msg_part in msg.message:
            if isinstance(msg_part, messages.MessagingServiceTextContent):
                scilog_msg.add_text(msg_part.content)
            elif isinstance(msg_part, messages.MessagingServiceFileContent):
                # We have to write the file to disk because the SciLog SDK only accepts file paths for attachments.
                if not tmp_dir:
                    tmp_dir = f"{self.temp_dir}/{uuid.uuid4()}"
                    os.makedirs(tmp_dir, exist_ok=True)
                file_name = msg_part.filename
                file_path = f"{tmp_dir}/{file_name}"
                with open(file_path, "wb") as f:
                    f.write(msg_part.data)
                files.append(file_path)
                scilog_msg.add_file(file_path)
            elif isinstance(msg_part, messages.MessagingServiceTagsContent):
                scilog_msg.add_tag(msg_part.tags)

        scilog_msg.send()
        # Cleanup files after sending the message to avoid leaving temporary files on disk.
        for file_path in files:
            try:
                print(f"Removing temporary file: {file_path}")
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Failed to remove temporary file {file_path}: {e}")
        # Remove the temporary directory
        if tmp_dir:
            try:
                os.rmdir(tmp_dir)
            except Exception as e:
                logger.error(f"Failed to remove temporary directory {tmp_dir}: {e}")
