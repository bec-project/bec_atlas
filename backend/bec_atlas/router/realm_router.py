from fastapi import APIRouter, Depends

from bec_atlas.authentication import get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import Realm, UserInfo
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

    async def realms(
        self, include_deployments: bool = False, current_user: UserInfo = Depends(get_current_user)
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

    async def realm_with_id(
        self, realm_id: str, current_user: UserInfo = Depends(get_current_user)
    ):
        """
        Get realm with id.

        Args:
            realm_id (str): The realm id

        Returns:
            Realm: The realm with the id
        """
        return self.db.find_one("realms", {"_id": realm_id}, Realm, user=current_user)
