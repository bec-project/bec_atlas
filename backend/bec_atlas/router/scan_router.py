from fastapi import APIRouter, Depends, Query

from bec_atlas.authentication import get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import ScanStatusPartial, UserInfo
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

    async def scans(
        self,
        session_id: str,
        include_user_data: bool = False,
        fields: list[str] = Query(default=None),
        offset: int = 0,
        limit: int = 100,
        current_user: UserInfo = Depends(get_current_user),
    ) -> list[ScanStatusPartial]:
        """
        Get all scans for a session.

        Args:
            session_id (str): The session id
        """
        if fields:
            fields = {field: 1 for field in fields}
        if include_user_data:
            include = [{"$match": {"session_id": session_id}}]
            if fields:
                include.append({"$project": fields})
            include += [
                {"$skip": offset},
                {"$limit": limit},
                {
                    "$lookup": {
                        "from": "scan_user_data",
                        "let": {"_id": "$_id"},
                        "pipeline": [{"$match": {"$expr": {"$eq": ["$_id", "$$_id"]}}}],
                        "as": "user_data",
                    }
                },
            ]
            return self.db.aggregate("scans", include, ScanStatusPartial, user=current_user)
        return self.db.find(
            "scans",
            {"session_id": session_id},
            ScanStatusPartial,
            limit=limit,
            offset=offset,
            fields=fields,
            user=current_user,
        )

    async def scans_with_id(
        self,
        scan_id: str,
        include_user_data: bool = False,
        current_user: UserInfo = Depends(get_current_user),
    ):
        """
        Get scan with id from session

        Args:
            scan_id (str): The scan id
        """
        return self.db.find_one("scans", {"_id": scan_id}, ScanStatusPartial, user=current_user)
