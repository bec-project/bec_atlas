from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query

from bec_atlas.authentication import convert_to_user, get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import BECAccessProfile, User
from bec_atlas.router.base_router import BaseRouter

if TYPE_CHECKING:  # pragma: no cover
    from bec_atlas.datasources.datasource_manager import DatasourceManager


class BECAccessRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources: DatasourceManager | None = None):
        super().__init__(prefix, datasources)

        if not self.datasources:
            raise RuntimeError("Datasources not loaded")

        self.db: MongoDBDatasource = self.datasources.mongodb
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/bec_access",
            self.get_bec_access,
            methods=["GET"],
            description="Retrieve the access key for a specific deployment and user.",
        )

    @convert_to_user
    async def get_bec_access(
        self,
        deployment_id: str,
        user: str = Query(None),
        current_user: User = Depends(get_current_user),
    ) -> dict:
        """
        Retrieve the access key for a specific deployment and user.

        Args:
            deployment_id (str): The deployment id
            user (str): The user name to retrieve the access key for. If not provided,
                the access key for the current user will be retrieved.
            current_user (User): The current user
        """
        if not user:
            user = current_user.email
        out = self.db.find_one(
            "bec_access_profiles",
            {"deployment_id": deployment_id, "username": user},
            BECAccessProfile,
            user=current_user,
        )

        if not out:
            raise HTTPException(status_code=404, detail="Access key not found.")

        # Return the newest access key
        timestamps = sorted(out.passwords.keys())
        return {"token": out.passwords[timestamps[-1]]}
