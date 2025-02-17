import secrets
from typing import TYPE_CHECKING

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from bec_atlas.authentication import convert_to_user, get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import DeploymentCredential, User
from bec_atlas.router.base_router import BaseRouter

if TYPE_CHECKING:  # pragma: no cover
    from bec_atlas.datasources.redis_datasource import RedisDatasource


class DeploymentCredentialsRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.db: MongoDBDatasource = self.datasources.datasources.get("mongodb")
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

    @convert_to_user
    async def deployment_credential(
        self, deployment_id: str, current_user: User = Depends(get_current_user)
    ) -> DeploymentCredential:
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

            # update the redis deployment key
            redis: RedisDatasource = self.datasources.datasources.get("redis")
            redis.add_deployment_acl(out)

            return out
        raise HTTPException(
            status_code=403, detail="User does not have permission to access this resource."
        )
