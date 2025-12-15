from __future__ import annotations

from bec_lib.logger import bec_logger

from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.datasources.redis_datasource import RedisDatasource
from bec_atlas.ingestor.scilog_logbook_manager import SciLogLogbookManager

logger = bec_logger.logger


class DatasourceManager:
    def __init__(self, config: dict):
        self.config = config
        self._redis: RedisDatasource = RedisDatasource(config["redis"])
        self._mongodb: MongoDBDatasource = MongoDBDatasource(config["mongodb"])
        self._scilog_logbook_manager: SciLogLogbookManager = SciLogLogbookManager(
            config=config["scilog"]
        )

    def connect(self):
        self.redis.connect()
        self.mongodb.connect()

    @property
    def redis(self) -> RedisDatasource:
        if not self._redis:
            raise RuntimeError("Redis datasource not loaded")
        return self._redis

    @property
    def mongodb(self) -> MongoDBDatasource:
        if not self._mongodb:
            raise RuntimeError("MongoDB datasource not loaded")
        return self._mongodb

    @property
    def scilog(self) -> SciLogLogbookManager:
        if not self._scilog_logbook_manager:
            raise RuntimeError("SciLog Logbook Manager not loaded")
        return self._scilog_logbook_manager

    def shutdown(self):
        self._redis.shutdown()
        self._mongodb.shutdown()
