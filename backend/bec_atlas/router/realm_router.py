from fastapi import APIRouter, Depends

from bec_atlas.authentication import convert_to_user, get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import DeploymentAccess, Realm, User
from bec_atlas.router.base_router import BaseRouter


class RealmRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.db: MongoDBDatasource = self.datasources.datasources.get("mongodb")
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/realms",
            self.realms,
            methods=["GET"],
            description="Get all realms",
            response_model=list[Realm],
            response_model_exclude_none=True,
        )
        self.router.add_api_route(
            "/realms/id",
            self.realm_with_id,
            methods=["GET"],
            description="Get a single realm by id",
            response_model=Realm,
            response_model_exclude_none=True,
        )
        self.router.add_api_route(
            "/realms/deployment_access",
            self.realm_with_deployment_access,
            methods=["GET"],
            description="Get all realms with deployment access",
            response_model=list[Realm],
            response_model_exclude_none=True,
        )

    @convert_to_user
    async def realms(
        self, include_deployments: bool = False, current_user: User = Depends(get_current_user)
    ) -> list[Realm]:
        """
        Get all realms.

        Args:
            include_deployments (bool): Include deployments in the response

        Returns:
            list[Realm]: List of realms
        """
        if include_deployments:
            include = [
                {
                    "$lookup": {
                        "from": "deployments",
                        "let": {"realm_id": "$_id"},
                        "pipeline": [{"$match": {"$expr": {"$eq": ["$realm_id", "$$realm_id"]}}}],
                        "as": "deployments",
                    }
                }
            ]
            return self.db.aggregate("realms", include, Realm, user=current_user)
        return self.db.find("realms", {}, Realm, user=current_user)

    @convert_to_user
    async def realm_with_deployment_access(
        self, owner_only: bool = False, current_user: User = Depends(get_current_user)
    ):
        """
        Get all realms with deployment access.

        Args:
            owner_only (bool): Only return realms where the current user is an owner of a deployment
            current_user (UserInfo): The current user

        Returns:
            list[Realm]: List of realms with deployment access
        """
        if owner_only:
            access = self.db.find("deployment_access", {}, DeploymentAccess, user=current_user)
        else:
            access = self.db.find("deployment_access", {}, DeploymentAccess)
        deployment_ids = [d.id for d in access]
        include = [
            {
                "$lookup": {
                    "from": "deployments",
                    "let": {"realm_id": "$_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$realm_id", "$$realm_id"]}}},
                        {"$match": {"_id": {"$in": deployment_ids}}},
                    ],
                    "as": "deployments",
                }
            },
            {"$match": {"deployments": {"$ne": []}}},
        ]
        return self.db.aggregate("realms", include, Realm, user=current_user)

    @convert_to_user
    async def realm_with_id(self, realm_id: str, current_user: User = Depends(get_current_user)):
        """
        Get realm with id.

        Args:
            realm_id (str): The realm id

        Returns:
            Realm: The realm with the id
        """
        return self.db.find_one("realms", {"_id": realm_id}, Realm, user=current_user)
