import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bec_atlas.datasources.datasource_manager import DatasourceManager
from bec_atlas.router.bec_access_router import BECAccessRouter
from bec_atlas.router.deployment_access_router import DeploymentAccessRouter
from bec_atlas.router.deployment_credentials import DeploymentCredentialsRouter
from bec_atlas.router.deployments_router import DeploymentsRouter
from bec_atlas.router.realm_router import RealmRouter
from bec_atlas.router.redis_router import RedisRouter, RedisWebsocket
from bec_atlas.router.scan_router import ScanRouter
from bec_atlas.router.session_router import SessionRouter
from bec_atlas.router.user_router import UserRouter

CONFIG = {
    "redis": {"host": "localhost", "port": 6380},
    "mongodb": {"host": "localhost", "port": 27017},
}

origins = ["http://localhost:4200", "http://localhost"]


class AtlasApp:
    API_VERSION = "v1"

    def __init__(self, config=None):
        self.prefix = f"/api/{self.API_VERSION}"
        self.config = config or CONFIG
        self.app = FastAPI(
            docs_url=f"{self.prefix}/docs",
            openapi_url=f"{self.prefix}/openapi.json",
            redoc_url=f"{self.prefix}/redoc",
            title="BEC Atlas API",
        )
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.server = None
        self.datasources = DatasourceManager(config=self.config)
        self.datasources.connect()
        self.register_event_handler()
        # self.add_routers()

    def register_event_handler(self):
        self.app.add_event_handler("shutdown", self.on_shutdown)
        self.app.add_event_handler("startup", self.on_startup)

    async def on_startup(self):
        self.add_routers()

    async def on_shutdown(self):
        self.datasources.shutdown()

    def add_routers(self):
        # pylint: disable=attribute-defined-outside-init
        if not self.datasources.redis or not self.datasources.mongodb:
            raise ValueError("Datasources not loaded")

        # User
        self.user_router = UserRouter(prefix=self.prefix, datasources=self.datasources)
        self.app.include_router(self.user_router.router, tags=["User"])

        # Realm
        self.realm_router = RealmRouter(prefix=self.prefix, datasources=self.datasources)
        self.app.include_router(self.realm_router.router, tags=["Realm"])

        # Deployment
        self.deployment_router = DeploymentsRouter(prefix=self.prefix, datasources=self.datasources)
        self.app.include_router(self.deployment_router.router, tags=["Deployment"])

        # Deployment Credentials
        self.deployment_credentials_router = DeploymentCredentialsRouter(
            prefix=self.prefix, datasources=self.datasources
        )
        self.app.include_router(
            self.deployment_credentials_router.router, tags=["Deployment Credentials"]
        )

        # Deployment Access
        self.deployment_access_router = DeploymentAccessRouter(
            prefix=self.prefix, datasources=self.datasources
        )
        self.app.include_router(self.deployment_access_router.router, tags=["Deployment Access"])

        # BEC Access
        self.bec_access_router = BECAccessRouter(prefix=self.prefix, datasources=self.datasources)
        self.app.include_router(self.bec_access_router.router, tags=["BEC Access"])

        # Session
        self.session_router = SessionRouter(prefix=self.prefix, datasources=self.datasources)
        self.app.include_router(self.session_router.router, tags=["Session"])

        # Scan
        self.scan_router = ScanRouter(prefix=self.prefix, datasources=self.datasources)
        self.app.include_router(self.scan_router.router, tags=["Scan"])

        # Redis
        self.redis_router = RedisRouter(prefix=self.prefix, datasources=self.datasources)
        self.app.include_router(self.redis_router.router, tags=["Redis"])

        self.redis_websocket = RedisWebsocket(
            prefix=self.prefix, datasources=self.datasources, app=self
        )
        self.app.mount("/", self.redis_websocket.app)

    def run(self, port=8000):  # pragma: no cover
        config = uvicorn.Config(self.app, host="localhost", port=port)
        self.server = uvicorn.Server(config=config)
        self.server.run()
        # uvicorn.run(self.app, host="localhost", port=port)


def main():  # pragma: no cover
    import argparse
    import logging

    from bec_atlas.utils.env_loader import load_env

    config = load_env()
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Run the BEC Atlas API")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the API on")

    args = parser.parse_args()
    horizon_app = AtlasApp(config=config)
    horizon_app.run(port=args.port)


if __name__ == "__main__":  # pragma: no cover
    main()
