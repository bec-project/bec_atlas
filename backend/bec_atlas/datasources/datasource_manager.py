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
        logger.info(f"Loading datasources with config: {self.config}")
        for datasource_name, datasource_config in self.config.items():
            if datasource_name == "redis":
                self.datasources[datasource_name] = RedisDatasource(datasource_config)
            if datasource_name == "mongodb":
                self.datasources[datasource_name] = MongoDBDatasource(datasource_config)

    def shutdown(self):
        for datasource in self.datasources.values():
            datasource.shutdown()
