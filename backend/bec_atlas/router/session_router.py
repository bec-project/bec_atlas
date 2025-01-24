import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from bec_atlas.authentication import create_access_token, get_current_user, verify_password
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model import UserInfo
from bec_atlas.model.model import Session
from bec_atlas.router.base_router import BaseRouter


class SessionRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.db: MongoDBDatasource = self.datasources.datasources.get("mongodb")
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/sessions",
            self.sessions,
            methods=["GET"],
            description="Get all sessions",
            response_model=list[Session],
            response_model_exclude_none=True,
        )
        self.router.add_api_route(
            "/sessions/realm",
            self.sessions_by_realm,
            methods=["GET"],
            description="Get all sessions for a realm",
            response_model=list[Session],
            response_model_exclude_none=True,
        )

    async def sessions(
        self,
        filter: str | None = None,
        fields: list[str] = Query(default=None),
        offset: int = 0,
        limit: int = 100,
        sort: str | None = None,
        current_user: UserInfo = Depends(get_current_user),
    ) -> list[Session]:
        """
        Get all sessions.

        Args:
            filter (str): JSON filter for the query, e.g. '{"name": "test"}'
            fields (list[str]): List of fields to return, e.g ["name", "description"]
            offset (int): Offset for the query
            limit (int): Limit for the query
            sort (str): Sort order for the query, e.g. '{"name": 1}' for ascending order,
                '{"name": -1}' for descending order. Multiple fields can be sorted by
                separating them with a comma, e.g. '{"name": 1, "description": -1}'
            current_user (UserInfo): The current user

        Returns:
            list[Sessions]: List of sessions

        """
        if fields:
            fields = {
                field: 1
                for field in fields
                if field in Session.model_json_schema()["properties"].keys()
            }
        return self.db.find(
            "sessions",
            filter,
            Session,
            fields=fields,
            offset=offset,
            limit=limit,
            sort=sort,
            user=current_user,
        )

    async def sessions_by_realm(
        self,
        realm_id: str,
        filter: str | None = None,
        fields: list[str] = Query(default=None),
        offset: int = 0,
        limit: int = 100,
        sort: str | None = None,
        current_user: UserInfo = Depends(get_current_user),
    ) -> list[Session]:
        """
        Get all sessions for a realm.
        """
        filters = {"realm_id": realm_id}
        if filter:
            filter = json.loads(filter)
            filters.update(filter)
        out = await self.sessions(filter, fields, offset, limit, sort, current_user)
        return out
