import socketio
import uvicorn
from bec_atlas.datasources.datasource_manager import DatasourceManager
from bec_atlas.router.redis_router import RedisRouter, RedisWebsocket
from bec_atlas.router.scan_router import ScanRouter
from bec_atlas.router.user import UserRouter
from fastapi import FastAPI

CONFIG = {"redis": {"host": "localhost", "port": 6380}, "scylla": {"hosts": ["localhost"]}}


class AtlasApp:
    API_VERSION = "v1"

    def __init__(self, config=None):
        self.config = config or CONFIG
        self.app = FastAPI()
        self.prefix = f"/api/{self.API_VERSION}"
        self.datasources = DatasourceManager(config=self.config)
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

    def run(self, port=8000):
        uvicorn.run(self.app, host="localhost", port=port)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run the BEC Atlas API")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the API on")

    args = parser.parse_args()
    horizon_app = AtlasApp()
    horizon_app.run(port=args.port)


if __name__ == "__main__":
    main()
