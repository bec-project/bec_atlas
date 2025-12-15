import secrets
import socket
from typing import TYPE_CHECKING

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from bec_atlas.authentication import convert_to_user, get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import DeploymentCredential, Deployments, User
from bec_atlas.router.base_router import BaseRouter

if TYPE_CHECKING:  # pragma: no cover
    from bec_atlas.datasources.redis_datasource import RedisDatasource


class DeploymentCredentialsRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        if not self.datasources:
            raise RuntimeError("Datasources not loaded")
        self.db: MongoDBDatasource = self.datasources.mongodb
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/deploymentCredentials",
            self.deployment_credential,
            methods=["GET"],
            description="Retrieve the deployment key for a specific deployment.",
            response_model=DeploymentCredential | None,
        )
        self.router.add_api_route(
            "/deploymentCredentials/refresh",
            self.refresh_deployment_credentials,
            methods=["POST"],
            description="Refresh the deployment key for a specific deployment.",
            response_model=DeploymentCredential,
        )
        self.router.add_api_route(
            "/deploymentCredentials/env",
            self.download_env_file,
            methods=["GET"],
            description="Download the environment file for a specific deployment.",
            response_class=PlainTextResponse,
        )

    @convert_to_user
    async def deployment_credential(
        self, deployment_id: str, current_user: User = Depends(get_current_user)
    ) -> DeploymentCredential | None:
        """
        Get the credentials for a deployment.

        Args:
            deployment_id (str): The deployment id
        """
        if not ObjectId.is_valid(deployment_id):
            raise HTTPException(status_code=400, detail="Invalid deployment ID")
        if set(current_user.groups) & set(["admin", "bec_group"]):
            out = self.db.find(
                "deployment_credentials", {"_id": ObjectId(deployment_id)}, DeploymentCredential
            )
            if len(out) > 0:
                return out[0]
            return None

        raise HTTPException(
            status_code=403, detail="User does not have permission to access this resource."
        )

    @convert_to_user
    async def download_env_file(
        self, deployment_name: str, current_user: User = Depends(get_current_user)
    ) -> PlainTextResponse:
        """
        Download the environment file for a deployment.

        Args:
            deployment_name (str): The deployment name, typically the hostname

        Returns:
            PlainTextResponse: The environment file content
        """

        if not set(current_user.groups) & set(["admin", "bec_group"]):
            # Only admin accounts can download the env file; typically done during the auto-deployment
            raise HTTPException(
                status_code=403, detail="User does not have permission to access this resource."
            )

        # Find the deployment by name
        deployment = self.db.find_one("deployments", {"name": deployment_name}, Deployments)
        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")

        # Get the deployment credentials
        credentials = self.db.find(
            "deployment_credentials", {"_id": deployment.id}, DeploymentCredential
        )

        if len(credentials) == 0:
            raise HTTPException(status_code=404, detail="Deployment credentials not found")

        credential = credentials[0]

        # Get Redis port from datasources config and use OS hostname
        if not self.datasources:
            raise RuntimeError("Datasources not loaded")
        hostname = socket.gethostname()

        # Generate the .env file content
        env_content = f"""ATLAS_HOST={hostname}:{self.datasources.redis.config.get('port', 6380)}
ATLAS_DEPLOYMENT={deployment.id}
ATLAS_KEY={credential.credential}
"""

        return PlainTextResponse(
            content=env_content,
            headers={
                "Content-Disposition": "attachment; filename=.env",
                "Content-Type": "text/plain; charset=utf-8",
            },
        )

    @convert_to_user
    async def refresh_deployment_credentials(
        self, deployment_id: str, current_user: User = Depends(get_current_user)
    ):
        """
        Refresh the deployment credentials.

        Args:
            deployment_id (str): The deployment id

        """
        if set(current_user.groups) & set(["admin", "bec_group"]):
            token = secrets.token_urlsafe(32)
            out = self.db.patch(
                "deployment_credentials",
                id=ObjectId(deployment_id),
                update={"credential": token},
                dtype=DeploymentCredential,
            )
            if out is None:
                raise HTTPException(status_code=404, detail="Deployment not found")

            deployment = self.db.find_one(
                "deployments", {"_id": ObjectId(deployment_id)}, Deployments
            )
            if not deployment:
                raise HTTPException(status_code=404, detail="Deployment not found")

            # update the redis deployment key
            if not self.datasources:
                raise RuntimeError("Datasources not loaded")
            redis: RedisDatasource = self.datasources.redis
            redis.add_deployment_acl(out, realm_id=deployment.realm_id)

            return out
        raise HTTPException(
            status_code=403, detail="User does not have permission to access this resource."
        )
