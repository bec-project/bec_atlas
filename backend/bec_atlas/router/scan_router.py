import json

from fastapi import APIRouter, Depends, Query

from bec_atlas.authentication import get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import ScanStatusPartial, ScanUserData, UserInfo
from bec_atlas.router.base_router import BaseRouter


class ScanRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.db: MongoDBDatasource = self.datasources.datasources.get("mongodb")
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/scans/session",
            self.scans,
            methods=["GET"],
            description="Get all scans for a session",
            response_model=list[ScanStatusPartial],
            response_model_exclude_none=True,
        )
        self.router.add_api_route(
            "/scans/id",
            self.scans_with_id,
            methods=["GET"],
            description="Get a single scan by id for a session",
            response_model=ScanStatusPartial,
            response_model_exclude_none=True,
        )
        self.router.add_api_route(
            "/scans/user_data",
            self.update_scan_user_data,
            methods=["PATCH"],
            description="Update the user data of a scan",
            response_model=dict,
        )
        self.router.add_api_route(
            "/scans/count",
            self.count_scans,
            methods=["GET"],
            description="Count the number of scans",
            response_model=dict,
        )

    async def scans(
        self,
        session_id: str,
        filter: str | None = None,
        fields: list[str] = Query(default=None),
        offset: int = 0,
        limit: int = 100,
        sort: str | None = None,
        current_user: UserInfo = Depends(get_current_user),
    ) -> list[ScanStatusPartial]:
        """
        Get all scans for a session.

        Args:
            session_id (str): The session id
            filter (str): JSON filter for the query, e.g. '{"name": "test"}'
            fields (list[str]): List of fields to return, e.g ["name", "description"]
            offset (int): Offset for the query
            limit (int): Limit for the query
            sort (str): Sort order for the query, e.g. '{"name": 1}' for ascending order,
                '{"name": -1}' for descending order. Multiple fields can be sorted by
                separating them with a comma, e.g. '{"name": 1, "description": -1}'
            current_user (UserInfo): The current user

        Returns:
            list[ScanStatusPartial]: List of scans
        """

        if fields:
            fields = {
                field: 1
                for field in fields
                if field in ScanStatusPartial.model_json_schema()["properties"].keys()
            }

        filters = {"session_id": session_id}
        if filter:
            filter = json.loads(filter)
            filters.update(filter)

        return self.db.find(
            "scans",
            filters,
            ScanStatusPartial,
            limit=limit,
            offset=offset,
            fields=fields,
            sort=sort,
            user=current_user,
        )

    async def scans_with_id(
        self,
        scan_id: str,
        fields: list[str] = Query(default=None),
        current_user: UserInfo = Depends(get_current_user),
    ):
        """
        Get scan with id from session

        Args:
            scan_id (str): The scan id
        """
        if fields:
            fields = {
                field: 1
                for field in fields
                if field in ScanStatusPartial.model_json_schema()["properties"].keys()
            }
        return self.db.find_one(
            collection="scans",
            query_filter={"_id": scan_id},
            dtype=ScanStatusPartial,
            user=current_user,
        )

    async def update_scan_user_data(
        self,
        scan_id: str,
        user_data: ScanUserData,
        current_user: UserInfo = Depends(get_current_user),
    ):
        """
        Update the user data of a scan in the database.

        Args:
            scan_id (str): The scan id
            user_data (dict): The user data to update
        """
        out = self.db.patch(
            "scans",
            id=scan_id,
            update={"user_data": user_data.model_dump(exclude_defaults=True)},
            dtype=ScanStatusPartial,
            user=current_user,
            return_document=True,
        )
        if out is None:
            return {"message": "Scan not found."}
        return {"message": "Scan user data updated."}

    async def count_scans(
        self, filter: str | None = None, current_user: UserInfo = Depends(get_current_user)
    ) -> int:
        """
        Count the number of scans.

        Args:
            filter (str): JSON filter for the query, e.g. '{"name": "test"}'
            current_user (UserInfo): The current user

        Returns:
            int: The number of scans
        """
        pipeline = []
        if filter:
            filter = json.loads(filter)
            pipeline.append({"$match": filter})
        pipeline.append({"$count": "count"})

        out = self.db.aggregate("scans", pipeline=pipeline, dtype=None, user=current_user)
        if out:
            return out[0]
