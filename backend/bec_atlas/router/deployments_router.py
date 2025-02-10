import json
from typing import TYPE_CHECKING

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from bec_atlas.authentication import get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import DeploymentCredential, Deployments, UserInfo
from bec_atlas.router.base_router import BaseRouter

if TYPE_CHECKING:  # pragma: no cover
    from bec_atlas.datasources.redis_datasource import RedisDatasource


class DeploymentsRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.db: MongoDBDatasource = self.datasources.datasources.get("mongodb")
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/deployments/realm",
            self.deployments,
            methods=["GET"],
            description="Get all deployments for the realm",
            response_model=list[Deployments],
        )
        self.router.add_api_route(
            "/deployments/id",
            self.deployment_with_id,
            methods=["GET"],
            description="Get a single deployment by id for a realm",
            response_model=Deployments,
        )
        self.update_available_deployments()

    async def deployments(
        self, realm: str, current_user: UserInfo = Depends(get_current_user)
    ) -> list[Deployments]:
        """
        Get all deployments for a realm.

        Args:
            realm (str): The realm id

        Returns:
            list[Deployments]: List of deployments for the realm
        """
        return self.db.find("deployments", {"realm_id": realm}, Deployments, user=current_user)

    async def deployment_with_id(
        self, deployment_id: str, current_user: UserInfo = Depends(get_current_user)
    ):
        """
        Get deployment with id from realm

        Args:
            scan_id (str): The scan id
        """
        if not ObjectId.is_valid(deployment_id):
            raise HTTPException(status_code=400, detail="Invalid deployment id")
        return self.db.find_one(
            "deployments", {"_id": ObjectId(deployment_id)}, Deployments, user=current_user
        )

    def update_available_deployments(self):
        """
        Update the available deployments.
        """
        self.available_deployments = self.db.find("deployments", {}, Deployments)
        credentials = self.db.find("deployment_credentials", {}, DeploymentCredential)

        redis: RedisDatasource = self.datasources.datasources.get("redis")
        msg = json.dumps([msg.model_dump() for msg in self.available_deployments])
        redis.connector.set_and_publish("deployments", msg)
        for deployment in credentials:
            redis.add_deployment_acl(deployment)
