from __future__ import annotations

from bec_lib.logger import bec_logger

from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.datasources.redis_datasource import RedisDatasource

logger = bec_logger.logger


class DatasourceManager:
    def __init__(self, config: dict):
        self.config = config
        self._redis: RedisDatasource | None = None
        self._mongodb: MongoDBDatasource | None = None
        self.load_datasources()

    def connect(self):
        self.redis.connect()
        self.mongodb.connect()

    def load_datasources(self):
        redis_config = self.config.get("redis")
        if redis_config:
            self._redis = RedisDatasource(redis_config)
        mongodb_config = self.config.get("mongodb")
        if mongodb_config:
            self._mongodb = MongoDBDatasource(mongodb_config)

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

    def shutdown(self):
        if self._redis:
            self._redis.shutdown()
        if self._mongodb:
            self._mongodb.shutdown()
