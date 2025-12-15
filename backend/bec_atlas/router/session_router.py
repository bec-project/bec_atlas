from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from bec_atlas.authentication import convert_to_user, get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import Session, SessionPartial, User
from bec_atlas.router.base_router import BaseRouter, CollectionQueryParamsWithInclude

if TYPE_CHECKING:  # pragma: no cover
    from bec_atlas.datasources.datasource_manager import DatasourceManager


class SessionRouter(BaseRouter):
    def __init__(self, datasources: DatasourceManager, prefix="/api/v1"):
        super().__init__(datasources, prefix)
        self.db: MongoDBDatasource = self.datasources.mongodb
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/sessions",
            self.sessions,
            methods=["GET"],
            description="Get all sessions",
            response_model=list[SessionPartial],
            response_model_exclude_none=True,
        )

    @convert_to_user
    async def sessions(
        self,
        query: CollectionQueryParamsWithInclude = Query(
            default_factory=CollectionQueryParamsWithInclude,
            description=(
                "Query parameters for filtering, sorting, paginating, and including relations."
            ),
            title="Session Query Parameters",
        ),
        current_user: User = Depends(get_current_user),
    ) -> list[SessionPartial] | JSONResponse:
        """
        Get all sessions.

        Args:
            query (CollectionQueryParamsWithInclude): The query parameters for filtering, sorting, and paginating sessions.
            current_user (User): The current user

        Returns:
            list[SessionPartial]: List of sessions

        """

        return self.find_with_query(
            collection="sessions",
            dtype=Session,
            dtype_partial=SessionPartial,
            query=query,
            user=current_user,
        )
