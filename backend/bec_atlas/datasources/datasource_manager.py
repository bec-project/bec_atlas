from bec_lib.logger import bec_logger

from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.datasources.redis_datasource import RedisDatasource

logger = bec_logger.logger


class DatasourceManager:
    def __init__(self, config: dict):
        self.config = config
        self.datasources = {}
        self.load_datasources()

    def connect(self):
        for datasource in self.datasources.values():
            datasource.connect()

    def load_datasources(self):
        for datasource_name, datasource_config in self.config.items():
            if datasource_name == "redis":
                logger.info(
                    f"Loading Redis datasource. Host: {datasource_config.get('host')}, Port: {datasource_config.get('port')}, Username: {datasource_config.get('username')}"
                )
                self.datasources[datasource_name] = RedisDatasource(datasource_config)
            if datasource_name == "mongodb":
                logger.info(
                    f"Loading MongoDB datasource. Host: {datasource_config.get('host')}, Port: {datasource_config.get('port')}, Username: {datasource_config.get('username')}"
                )
                self.datasources[datasource_name] = MongoDBDatasource(datasource_config)

    def shutdown(self):
        for datasource in self.datasources.values():
            datasource.shutdown()
