from bec_atlas.authentication import get_current_user
from bec_atlas.models import User
from bec_atlas.router.base_router import BaseRouter
from fastapi import APIRouter, Depends


class ScanRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.scylla = self.datasources.datasources.get("scylla")
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route("/scan", self.scan, methods=["GET"])
        self.router.add_api_route("/scan/{scan_id}", self.scan_with_id, methods=["GET"])

    async def scan(self, current_user: User = Depends(get_current_user)):
        return self.scylla.get("scan", current_user=current_user)

    async def scan_with_id(self, scan_id: str):
        return {"scan_id": scan_id}
