"""
A module for fetching all available logbooks from SciLog and storing them in redis for
quick access.
"""

import datetime
import json

import requests
from bec_lib import messages
from bec_lib.endpoints import MessageEndpoints
from bec_lib.logger import bec_logger
from bec_lib.redis_connector import RedisConnector

XNAME_functional_account = {
    "x01da": "slsdebye@psi.ch",
    "x02da": "slstomcat@psi.ch",
    "x03da": "slspearl@psi.ch",
    "x04sa": "slsms@psi.ch",  #
    "x05la": "slsmicroxas@psi.ch",  #
    "x06da": "slsmx@psi.ch",  #
    "x07da": "slspollux@psi.ch",
    "x07db": "slsiss@psi.ch",
    "x07ma": "slsxtreme@psi.ch",
    "x09la": "slssis@psi.ch",
    "x09lb": "slsxil@psi.ch",
    "x10da": "slssuper-xas@psi.ch",
    "x10sa": "slsmx@psi.ch",  #
    "x11ma": "slssim@psi.ch",
    "x12sa": "slscsaxs@psi.ch",
}


def get_token(username: str, password: str) -> str:
    """
    Get an authentication token from SciLog.

    Args:
        username (str): The username.
        password (str): The password.
    Returns:
        str: The authentication token.
    """

    response = requests.post(
        "https://scilog.psi.ch/api/v1/users/login",
        json={"principal": username, "password": password},
        headers={"accept": "application/json", "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("token")


class SciLogLogbookManager:
    scilog_base_url = "https://scilog.psi.ch/api/v1"

    def __init__(self, redis_connector: RedisConnector, token: str):
        self.redis = redis_connector
        self.token = token

    def fetch_logbooks_for_realm(
        self, realm_xname: str, reference_date: str | None = None
    ) -> list[dict]:
        """
        Fetch all logbooks for a given realm from SciLog.

        Args:
            realm_xname (str): The xname of the realm.
            reference_date (str | None): The reference date as an ISO 8601 string. If provided, only logbooks updated after this date will be fetched.
        Returns:
            list[dict]: A list of logbooks.
        """

        filter_obj = {"where": {"updateACL": {"in": [XNAME_functional_account[realm_xname]]}}}

        if reference_date is not None:
            iso_date = reference_date
            filter_obj["where"]["updatedAt"] = {"gt": iso_date}

        params = {"filter": json.dumps(filter_obj)}
        headers = {"accept": "application/json", "Authorization": f"Bearer {self.token}"}

        response = requests.get(
            f"{self.scilog_base_url}/logbooks", headers=headers, params=params, timeout=30
        )
        response.raise_for_status()
        return response.json()

    def update_redis_logbooks(self, realm_xname: str):
        """
        Update the logbooks in redis for a given realm.

        Args:
            realm_xname (str): The xname of the realm.
        """

        logbooks = self.fetch_logbooks_for_realm(realm_xname)
        self.redis.set(
            MessageEndpoints.available_logbooks(realm_name=realm_xname),
            messages.AvailableResourceMessage(resource=logbooks),
        )
        bec_logger.logger.info(
            f"Updated {len(logbooks)} logbooks in redis for realm {realm_xname}."
        )


if __name__ == "__main__":

    from bec_atlas.utils.env_loader import load_env

    logger = bec_logger.logger
    config = load_env()
    token = get_token(username=config["scilog"]["username"], password=config["scilog"]["password"])
    redis_host = config.get("redis", {}).get("host", "localhost")
    redis_port = config.get("redis", {}).get("port", 6380)
    redis_connector = RedisConnector(f"{redis_host}:{redis_port}")
    username = config.get("redis", {}).get("username", "ingestor")
    password = config.get("redis", {}).get("password")
    redis_connector.authenticate(password=password, username=username)

    reference_date = (datetime.datetime.now() - datetime.timedelta(days=100)).isoformat() + "Z"

    logbook_manager = SciLogLogbookManager(redis_connector, token)
    for realm in XNAME_functional_account:
        logbook_manager.update_redis_logbooks(realm)

    redis_connector.shutdown()
