from fastapi import APIRouter

from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import Realm
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
            description="Get all deployments for the realm",
            response_model=list[Realm],
        )
        self.router.add_api_route(
            "/realms/{realm_id}",
            self.realm_with_id,
            methods=["GET"],
            description="Get a single deployment by id for a realm",
            response_model=Realm,
        )

    async def realms(self) -> list[Realm]:
        """
        Get all realms.

        Returns:
            list[Realm]: List of realms
        """
        return self.db.find("realms", {}, Realm)

    async def realm_with_id(self, realm_id: str):
        """
        Get realm with id.

        Args:
            realm_id (str): The realm id

        Returns:
            Realm: The realm with the id
        """
        return self.db.find_one("realms", {"_id": realm_id}, Realm)
