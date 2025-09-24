from __future__ import annotations

import json

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from bec_atlas.authentication import convert_to_user, get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import ScanStatusPartial, ScanUserData, User, UserInfo
from bec_atlas.router.base_router import BaseRouter


class ScanRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.db: MongoDBDatasource = self.datasources.mongodb
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

    @convert_to_user
    async def scans(
        self,
        session_id: str,
        filter: str | None = None,
        fields: list[str] = Query(default=None),
        offset: int = 0,
        limit: int = 100,
        sort: str | None = None,
        current_user: User = Depends(get_current_user),
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
            current_user (User): The current user

        Returns:
            list[ScanStatusPartial]: List of scans
        """

        if fields:
            fields = self._update_fields(fields)

        if not ObjectId.is_valid(session_id):
            raise HTTPException(status_code=400, detail="Invalid session ID")
        filters = {"session_id": session_id}

        if filter:
            filter = self._update_filter(filter)
            filters.update(filter)

        if sort:
            sort = self._update_sort(sort)

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

    @convert_to_user
    async def scans_with_id(
        self,
        scan_id: str,
        fields: list[str] = Query(default=None),
        current_user: User = Depends(get_current_user),
    ):
        """
        Get scan with id from session

        Args:
            scan_id (str): The scan id
        """
        if fields:
            fields = self._update_fields(fields)
        result = self.db.find_one(
            collection="scans",
            query_filter={"_id": scan_id},
            dtype=ScanStatusPartial,
            fields=fields,
            user=current_user,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Scan not found")
        return result

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
        current_user = self.get_user_from_db(current_user.token, current_user.email)
        out = self.db.patch(
            "scans",
            id=scan_id,
            update={"user_data": user_data.model_dump(exclude_defaults=True)},
            dtype=ScanStatusPartial,
            user=current_user,
            return_document=True,
        )
        if out is None:
            raise HTTPException(status_code=404, detail="Scan not found")
        return {"message": "Scan user data updated."}

    @convert_to_user
    async def count_scans(
        self, filter: str | None = None, current_user: User = Depends(get_current_user)
    ) -> int:
        """
        Count the number of scans.

        Args:
            filter (str): JSON filter for the query, e.g. '{"name": "test"}'
            current_user (User): The current user

        Returns:
            int: The number of scans
        """
        pipeline = []
        if filter:
            filter = self._update_filter(filter)
            pipeline.append({"$match": filter})
        pipeline.append({"$count": "count"})

        out = self.db.aggregate("scans", pipeline=pipeline, dtype=None, user=current_user)
        if out:
            return out[0]
        # I don't think this will ever be reached
        else:  # pragma: no cover
            return {"count": 0}

    def _update_filter(self, filter: str) -> dict:
        """
        Update the filter for the query.

        Args:
            filter (str): JSON filter for the query, e.g. '{"name": "test"}'

        Returns:
            dict: The filter for the query
        """
        exc = HTTPException(status_code=400, detail="Invalid filter. Must be a JSON object.")
        try:
            filter = json.loads(filter)
        except json.JSONDecodeError:
            # pylint: disable=raise-missing-from
            raise exc
        if not isinstance(filter, dict):
            raise exc
        return filter

    def _update_fields(self, fields: list[str]) -> dict:
        """
        Update the fields to return in the query.

        Args:
            fields (list[str]): List of fields to return

        Returns:
            dict: The fields to return
        """
        exc = HTTPException(
            status_code=400, detail="Invalid fields. Must be a list of valid fields."
        )
        if not all(
            field in ScanStatusPartial.model_json_schema()["properties"].keys() for field in fields
        ):
            raise exc
        fields = {field: 1 for field in fields}
        return fields

    def _update_sort(self, sort: str) -> dict:
        """
        Update the sort order for the query.

        Args:
            sort (str): Sort order for the query, e.g. '{"name": 1}' for ascending order,
                '{"name": -1}' for descending order. Multiple fields can be sorted by
                separating them with a comma, e.g. '{"name": 1, "description": -1}'

        Returns:
            dict: The sort order
        """
        exc = HTTPException(
            status_code=400, detail="Invalid sort order. Must be a JSON object with valid keys."
        )
        try:
            sort = json.loads(sort)
        except json.JSONDecodeError:
            # pylint: disable=raise-missing-from
            raise exc
        if not isinstance(sort, dict):
            raise exc
        if not all(
            key in ScanStatusPartial.model_json_schema()["properties"].keys() for key in sort.keys()
        ):
            raise exc
        return sort
