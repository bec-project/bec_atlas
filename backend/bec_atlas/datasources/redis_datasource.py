from __future__ import annotations

from typing import TYPE_CHECKING

from bec_lib.redis_connector import RedisConnector
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import AuthenticationError

if TYPE_CHECKING:
    from bec_atlas.model.model import Deployments


class RedisDatasource:
    def __init__(self, config: dict):
        self.config = config
        self.connector = RedisConnector(f"{config.get('host')}:{config.get('port')}")
        username = config.get("username")
        password = config.get("password")

        try:
            self.connector._redis_conn.auth(password, username=username)
            self.reconfigured_acls = False
        except AuthenticationError:
            self.setup_acls()
            self.connector._redis_conn.auth(password, username=username)
            self.reconfigured_acls = True

        self.connector._redis_conn.connection_pool.connection_kwargs["username"] = username
        self.connector._redis_conn.connection_pool.connection_kwargs["password"] = password

        self.async_connector = AsyncRedis(
            host=config.get("host"),
            port=config.get("port"),
            username="ingestor",
            password=config.get("password"),
        )
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

    def add_deployment_acl(self, deployment: Deployments):
        """
        Add ACLs for the deployment.

        Args:
            deployment (Deployments): The deployment object
        """
        print(f"Adding ACLs for deployment <{deployment.name}>({deployment.id})")
        self.connector._redis_conn.acl_setuser(
            f"ingestor_{deployment.id}",
            enabled=True,
            passwords=f"+{deployment.deployment_key}",
            categories=["+@all", "-@dangerous"],
            keys=[
                f"internal/deployment/{deployment.id}/*",
                f"internal/deployment/{deployment.id}/*/state",
                f"internal/deployment/{deployment.id}/*/data/*",
            ],
            channels=[
                f"internal/deployment/{deployment.id}/*/state",
                f"internal/deployment/{deployment.id}/*",
                f"internal/deployment/{deployment.id}/request",
                f"internal/deployment/{deployment.id}/request_response/*",
            ],
            commands=[f"+keys|internal/deployment/{deployment.id}/*/state"],
            reset_channels=True,
            reset_keys=True,
        )

    def connect(self):
        pass

    def shutdown(self):
        self.connector.shutdown()
