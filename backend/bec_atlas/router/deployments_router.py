from fastapi import APIRouter, Depends

from bec_atlas.authentication import get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import Deployments, UserInfo
from bec_atlas.router.base_router import BaseRouter


class DeploymentsRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.db: MongoDBDatasource = self.datasources.datasources.get("mongodb")
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/deployments/realm/{realm}",
            self.deployments,
            methods=["GET"],
            description="Get all deployments for the realm",
            response_model=list[Deployments],
        )
        self.router.add_api_route(
            "/deployments/id/{deployment_id}",
            self.deployment_with_id,
            methods=["GET"],
            description="Get a single deployment by id for a realm",
            response_model=Deployments,
        )

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
        return self.db.find_one(
            "deployments", {"_id": deployment_id}, Deployments, user=current_user
        )
