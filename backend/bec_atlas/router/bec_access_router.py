from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query

from bec_atlas.authentication import convert_to_user, get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import BECAccessProfile, User
from bec_atlas.router.base_router import BaseRouter
from bec_atlas.router.user_router import UserLoginRequest

if TYPE_CHECKING:  # pragma: no cover
    from bec_atlas.datasources.datasource_manager import DatasourceManager
    from bec_atlas.main import AtlasApp


class BECAccessRouter(BaseRouter):
    def __init__(
        self,
        prefix="/api/v1",
        datasources: DatasourceManager | None = None,
        app: AtlasApp | None = None,
    ):
        super().__init__(prefix, datasources)
        self.app = app

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
        self.router.add_api_route(
            "/bec_access_login",
            self.get_bec_access_login,
            methods=["POST"],
            description="Login and retrieve the access key for a specific deployment and user.",
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
        out = self._retrieve_access_account(deployment_id, user, current_user=current_user)
        return out

    async def get_bec_access_login(
        self, user_login: UserLoginRequest, deployment_id: str, user: str
    ) -> dict:
        """
        Login and retrieve the access key for a specific deployment and user.
        Exactly the same as get_bec_access, but with a login step to avoid the need
        for an access token only to retrieve the ACL key.

        Args:
            deployment_id (str): The deployment id
            user (str): The user name to retrieve the access key for
            password (str): The password for the user
        """
        if not self.app:
            raise RuntimeError("App not loaded")

        user_info = self.app.user_router._get_user(user_login)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found.")
        current_user = self.db.get_user_by_email(user_info.email)
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found.")
        out = self._retrieve_access_account(deployment_id, user, current_user=current_user)
        return out

    def _retrieve_access_account(
        self, deployment_id: str, username: str, current_user: User
    ) -> dict:

        out = self.db.find_one(
            "bec_access_profiles",
            {"deployment_id": deployment_id, "username": username},
            BECAccessProfile,
            user=current_user,
        )

        if not out:
            raise HTTPException(status_code=404, detail="Access key not found.")

        # Return the newest access key
        timestamps = sorted(out.passwords.keys())
        return {"token": out.passwords[timestamps[-1]]}
