from bec_atlas.datasources.redis_datasource import RedisDatasource
from bec_atlas.datasources.scylladb.scylladb import ScylladbDatasource


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
            if datasource_name == "scylla":
                self.datasources[datasource_name] = ScylladbDatasource(datasource_config)
            if datasource_name == "redis":
                self.datasources[datasource_name] = RedisDatasource(datasource_config)

    def shutdown(self):
        for datasource in self.datasources.values():
            datasource.shutdown()
