class BaseRouter:
    def __init__(self, prefix: str = "/api/v1", datasources=None) -> None:
        self.datasources = datasources
        self.prefix = prefix
