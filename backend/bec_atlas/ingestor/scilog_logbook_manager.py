"""
A module for fetching all available logbooks from SciLog and storing them in redis for
quick access.
"""

import json
import threading

import requests
from bec_lib.logger import bec_logger
from bec_lib.redis_connector import RedisConnector


class SciLogLogbookManager:
    scilog_base_url = "https://scilog.psi.ch/api/v1"

    def __init__(self, redis_connector: RedisConnector, token: str):
        self.redis = redis_connector
        self.token = token

    def fetch_logbooks_for_realm(self, realm_xname: str) -> list[dict]:
        """
        Fetch all logbooks for a given realm from SciLog.

        Args:
            realm_xname (str): The xname of the realm.
        Returns:
            list[dict]: A list of logbooks.
        """

        filter_obj = {
            "fields": {"id": True, "name": True, "description": True},
            "where": {"updateACL": {"in": ["slscsaxs@psi.ch"]}},
        }

        params = {"filter": json.dumps(filter_obj)}

        headers = {"accept": "application/json", "Authorization": f"Bearer {self.token}"}

        response = requests.get(
            f"{self.scilog_base_url}/logbooks", headers=headers, params=params, timeout=30
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    from bec_atlas.utils.env_loader import load_env

    logger = bec_logger.logger
    config = load_env()
    redis_connector = RedisConnector("localhost:6380")

    logbook_manager = SciLogLogbookManager(redis_connector)
    logbook_manager.fetch_logbooks_for_realm("")
