import json

from fastapi import APIRouter, Depends, Query

from bec_atlas.authentication import convert_to_user, get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import Session, User
from bec_atlas.router.base_router import BaseRouter


class SessionRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.db: MongoDBDatasource = self.datasources.mongodb
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

    @convert_to_user
    async def sessions(
        self,
        filter: str | None = None,
        fields: list[str] = Query(default=None),
        offset: int = 0,
        limit: int = 100,
        sort: str | None = None,
        current_user: User = Depends(get_current_user),
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
            current_user (User): The current user

        Returns:
            list[Sessions]: List of sessions

        """
        if fields:
            fields = {
                field: 1
                for field in fields
                if field in Session.model_json_schema()["properties"].keys()
            }

        if sort:
            sort = json.loads(sort)

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

    @convert_to_user
    async def sessions_by_realm(
        self,
        realm_id: str,
        filter: str | None = None,
        fields: list[str] = Query(default=None),
        offset: int = 0,
        limit: int = 100,
        sort: str | None = None,
        current_user: User = Depends(get_current_user),
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
