from __future__ import annotations

from typing import TYPE_CHECKING

from bec_lib.redis_connector import RedisConnector
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import AuthenticationError

if TYPE_CHECKING:
    from bec_atlas.model.model import DeploymentCredential


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

    def add_deployment_acl(self, deployment_credential: DeploymentCredential):
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

    def connect(self):
        pass

    def shutdown(self):
        self.connector.shutdown()
