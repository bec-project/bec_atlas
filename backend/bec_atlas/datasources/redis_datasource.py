from __future__ import annotations

from typing import TYPE_CHECKING

from bec_lib import messages
from bec_lib.codecs import BECCodec
from bec_lib.endpoints import MessageEndpoints
from bec_lib.redis_connector import RedisConnector
from bec_lib.serialization import msgpack
from bson import ObjectId
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import AuthenticationError, ResponseError

from bec_atlas.model import (
    AvailableMessagingServiceInfo,
    SciLogServiceInfo,
    SignalServiceInfo,
    TeamsServiceInfo,
)

if TYPE_CHECKING:
    from bec_atlas.model.model import DeploymentCredential, Deployments


class ObjectIdCodec(BECCodec):
    obj_type: list[type] = [ObjectId]

    @staticmethod
    def encode(obj):
        return str(obj)

    @staticmethod
    def decode(typename: str, data):
        return data


msgpack.register_codec(ObjectIdCodec)


class RedisDatasource:
    def __init__(self, config: dict):
        self.config = config

        if config.get("sync_instance"):
            self.connector = config.get("sync_instance")
        else:
            self.connector = RedisConnector(f"{config.get('host')}:{config.get('port')}")
        username = config.get("username")
        password = config.get("password")

        try:
            self.connector.authenticate(username=username, password=password)
            self.reconfigured_acls = False
        except (AuthenticationError, ResponseError):
            self.setup_acls()
            self.connector.authenticate(username=username, password=password)
            self.reconfigured_acls = True

        if config.get("async_instance"):
            self.async_connector = config.get("async_instance")
        else:
            self.async_connector = AsyncRedis(
                host=config.get("host"),
                port=config.get("port"),
                username=config.get("username"),
                password=config.get("password"),
            )
        self.connector.set_retry_enabled(True)
        print("Connected to Redis")

    def setup_acls(self):
        """
        Setup the ACLs for the Redis proxy server.
        """

        # Create the ingestor user. This user is used by the data ingestor to write data to the database.
        self.connector._redis_conn.acl_setuser(
            "ingestor",
            enabled=True,
            passwords=f'+{self.config.get("password")}',
            categories=["+@all"],
            keys=["*"],
            channels=["*"],
        )

        self.connector._redis_conn.acl_setuser(
            "user",
            enabled=True,
            passwords="+user",
            categories=["+@all"],
            keys=["*"],
            channels=["*"],
        )
        self.connector._redis_conn.acl_setuser(
            "default", enabled=True, categories=["-@all"], commands=["+auth", "+acl|whoami"]
        )

    def add_deployment_acl(self, deployment_credential: DeploymentCredential, realm_id: str):
        """
        Add ACLs for the deployment.

        Args:
            deployment (Deployments): The deployment object
        """
        print(f"Adding ACLs for deployment {deployment_credential.id}")
        dep_id = deployment_credential.id
        dep_key = deployment_credential.credential
        self.connector._redis_conn.acl_setuser(
            f"ingestor_{dep_id}",
            enabled=True,
            passwords=f"+{dep_key}",
            categories=["+@all", "-@dangerous"],
            keys=[
                f"internal/deployment/{dep_id}/*",
                f"internal/deployment/{dep_id}/*/state",
                f"internal/deployment/{dep_id}/*/data/*",
                f"internal/deployment/{dep_id}/bec_access",
                f"internal/deployment/{dep_id}/deployment_info",
                f"%R~internal/realm/{realm_id}/info/*",
            ],
            channels=[
                f"internal/deployment/{dep_id}/*/state",
                f"internal/deployment/{dep_id}/*",
                f"internal/deployment/{dep_id}/request",
                f"internal/deployment/{dep_id}/request_response/*",
                f"internal/deployment/{dep_id}/bec_access",
            ],
            commands=[f"+keys|internal/deployment/{dep_id}/*/state"],
            reset_channels=True,
            reset_keys=True,
        )

    def update_deployment_info(self, deployment: Deployments):
        """
        Update the deployment info in Redis.

        Args:
            deployment (Deployments): The deployment object
        """

        messaging_services = deployment.messaging_services or []

        if messaging_services:
            messaging_services = self._convert_messaging_services(messaging_services)

        if active_session := deployment.active_session:
            if active_session.messaging_services:
                active_session.messaging_services = self._convert_messaging_services(
                    active_session.messaging_services
                )
            active_session = messages.SessionInfoMessage(**active_session.model_dump())
        msg = messages.DeploymentInfoMessage(
            deployment_id=str(deployment.id),
            name=deployment.name,
            messaging_config=deployment.messaging_config,
            messaging_services=messaging_services,
            active_session=(active_session if deployment.active_session else None),
        )
        self.connector.xadd(
            MessageEndpoints.atlas_deployment_info(deployment_name=str(deployment.id)),
            {"data": msg},
            max_size=1,
            approximate=False,
        )

    def _convert_messaging_services(
        self, messaging_services: list[AvailableMessagingServiceInfo]
    ) -> list[AvailableMessagingServiceInfo]:
        """
        Convert the messaging services from the database format to the format used in the messages.

        Args:
            messaging_services (list[AvailableMessagingServiceInfo]): The list of messaging services from the database
        Returns:
            list[AvailableMessagingServiceInfo]: The list of messaging services in the format used in the messages
        """
        converted_services = []
        for service in messaging_services:
            content = service.model_dump()
            _id = str(content.pop("id"))
            try:
                match service.service_type:
                    case "scilog":
                        converted_services.append(SciLogServiceInfo(_id=_id, **content))
                    case "signal":
                        converted_services.append(SignalServiceInfo(_id=_id, **content))
                    case "teams":
                        converted_services.append(TeamsServiceInfo(_id=_id, **content))
            except Exception as exc:
                print(f"Error converting messaging service with id {_id}: {exc}")
        return converted_services

    def connect(self):
        pass

    def shutdown(self):
        self.connector.shutdown()
