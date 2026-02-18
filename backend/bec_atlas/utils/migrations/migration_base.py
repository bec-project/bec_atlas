from abc import ABC, abstractmethod

from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource


class BaseMigration(ABC):
    """
    Base class for all database migrations.

    Each migration should inherit from this class and implement the `run` method.
    The migration name is derived from the class name.
    """

    def __init__(self, config: dict):
        self.config = config
        self.datasource = MongoDBDatasource(config=self.config)
        self.datasource.connect(include_setup=False)

    @property
    def name(self) -> str:
        """Get the migration name from the class name."""
        return self.__class__.__name__

    @abstractmethod
    def run(self) -> None:
        """
        Execute the migration. This method must be implemented by subclasses.

        Raises:
            Exception: If the migration fails, raise an exception with details.
        """
        pass

    def get_metadata(self) -> dict:
        """
        Get metadata about this migration. Can be overridden by subclasses.

        Returns:
            dict: Metadata dictionary with optional description and version info
        """
        return {
            "description": self.__doc__ or "No description provided",
            "class_name": self.__class__.__name__,
        }
