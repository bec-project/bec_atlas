from fastapi import APIRouter, Depends

from bec_atlas.authentication import get_current_user
from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model.model import ScanStatus, UserInfo
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
            response_model=list[ScanStatus],
        )
        self.router.add_api_route(
            "/scans/id",
            self.scans_with_id,
            methods=["GET"],
            description="Get a single scan by id for a session",
            response_model=ScanStatus,
        )

    async def scans(
        self, session_id: str, current_user: UserInfo = Depends(get_current_user)
    ) -> list[ScanStatus]:
        """
        Get all scans for a session.

        Args:
            session_id (str): The session id
        """
        return self.db.find("scans", {"session_id": session_id}, ScanStatus, user=current_user)

    async def scans_with_id(self, scan_id: str, current_user: UserInfo = Depends(get_current_user)):
        """
        Get scan with id from session

        Args:
            scan_id (str): The scan id
        """
        return self.db.find_one("scans", {"_id": scan_id}, ScanStatus, user=current_user)
