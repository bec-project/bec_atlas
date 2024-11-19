import socketio
import uvicorn
from fastapi import FastAPI

from bec_atlas.datasources.datasource_manager import DatasourceManager
from bec_atlas.router.redis_router import RedisRouter, RedisWebsocket
from bec_atlas.router.scan_router import ScanRouter
from bec_atlas.router.user import UserRouter

CONFIG = {"redis": {"host": "localhost", "port": 6379}, "scylla": {"hosts": ["localhost"]}}


class HorizonApp:
    API_VERSION = "v1"

    def __init__(self):
        self.app = FastAPI()
        self.prefix = f"/api/{self.API_VERSION}"
        self.datasources = DatasourceManager(config=CONFIG)
        self.register_event_handler()
        self.add_routers()

    def register_event_handler(self):
        self.app.add_event_handler("startup", self.on_startup)
        self.app.add_event_handler("shutdown", self.on_shutdown)

    async def on_startup(self):
        self.datasources.connect()

    async def on_shutdown(self):
        self.datasources.shutdown()

    def add_routers(self):
        if not self.datasources.datasources:
            raise ValueError("Datasources not loaded")
        if "scylla" in self.datasources.datasources:
            self.scan_router = ScanRouter(prefix=self.prefix, datasources=self.datasources)
            self.app.include_router(self.scan_router.router)
            self.user_router = UserRouter(prefix=self.prefix, datasources=self.datasources)
            self.app.include_router(self.user_router.router)

        if "redis" in self.datasources.datasources:
            self.redis_websocket = RedisWebsocket(prefix=self.prefix, datasources=self.datasources)
            self.app.mount("/", self.redis_websocket.app)

    def run(self):
        uvicorn.run(self.app, host="localhost", port=8000)


if __name__ == "__main__":
    horizon_app = HorizonApp()
    horizon_app.run()
