from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from bec_lib.endpoints import EndpointInfo, MessageOp

if TYPE_CHECKING:
    from bec_lib import messages


class RedisAtlasEndpoints:
    """
    This class contains the endpoints for the Redis API. It is used to
    manage the subscriptions and the state information for the websocket
    """

    @staticmethod
    def websocket_state(deployment: str, host_id: str):
        """
        Endpoint for the websocket state information, containing the users and their subscriptions
        per backend host.

        Args:
            deployment (str): The deployment name
            host_id (str): The host id of the backend

        Returns:
            str: The endpoint for the websocket state information
        """
        return f"internal/deployment/{deployment}/{host_id}/state"

    @staticmethod
    def redis_data(deployment: str, endpoint: str):
        """
        Endpoint for the redis data for a deployment and endpoint.

        Args:
            deployment (str): The deployment name
            endpoint (str): The endpoint name

        Returns:
            str: The endpoint for the redis data
        """
        return f"internal/deployment/{deployment}/data/{endpoint}"

    @staticmethod
    def socketio_endpoint_room(deployment: str, endpoint: str):
        """
        Endpoint for the socketio room for an endpoint.

        Args:
            endpoint (str): The endpoint name

        Returns:
            str: The endpoint for the socketio room
        """
        return f"socketio/rooms/{deployment}/{endpoint}"

    @staticmethod
    def redis_request(deployment: str):
        """
        Endpoint for the redis request for a deployment and endpoint.

        Args:
            deployment (str): The deployment name

        Returns:
            str: The endpoint for the redis request
        """
        return f"internal/deployment/{deployment}/request"

    @staticmethod
    def redis_request_response(deployment: str, request_id: str):
        """
        Endpoint for the redis request response for a deployment and endpoint.

        Args:
            deployment (str): The deployment name
            request_id (str): The request id

        Returns:
            str: The endpoint for the redis request response
        """
        return f"internal/deployment/{deployment}/request_response/{request_id}"

    @staticmethod
    def redis_bec_acl_user(deployment_id: str):
        """
        Endpoint for the redis BEC ACL user for a deployment.

        Args:
            deployment_id (str): The deployment id

        Returns:
            str: The endpoint for the redis BEC ACL user
        """
        return f"internal/deployment/{deployment_id}/bec_access"

    @staticmethod
    def deployments():
        """
        Endpoint for the deployments information.

        Returns:
            str: The endpoint for the deployments information
        """
        return "deployments"

    @staticmethod
    def deployment_ingest(deployment_id: str):
        """
        Endpoint for the data ingestion for a deployment.

        Args:
            deployment_id (str): The deployment id
        Returns:
            str: The endpoint for the data ingestion
        """
        return f"internal/deployment/{deployment_id}/ingest"

    @staticmethod
    def available_logbooks(realm_id: str):
        """
        Endpoint for the available logbooks for a realm.

        Args:
            realm_id (str): The realm id
        Returns:
            str: The endpoint for the available logbooks
        """
        return f"internal/{realm_id}/info/logbooks"
