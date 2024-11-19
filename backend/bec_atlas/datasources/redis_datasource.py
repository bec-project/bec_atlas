from bec_lib.redis_connector import RedisConnector


class RedisDatasource:
    def __init__(self, config: dict):
        self.config = config
        self.connector = RedisConnector(f"{config.get('host')}:{config.get('port')}")

    def connect(self):
        pass

    def shutdown(self):
        self.connector.shutdown()
