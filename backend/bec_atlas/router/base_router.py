from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from bec_atlas.model.model import User

if TYPE_CHECKING:  # pragma: no cover
    from bec_atlas.datasources.datasource_manager import DatasourceManager


class BaseRouter:
    def __init__(
        self, prefix: str = "/api/v1", datasources: DatasourceManager | None = None
    ) -> None:
        self.datasources = datasources
        self.prefix = prefix
        if not self.datasources:
            raise RuntimeError("Datasources not loaded")

    @lru_cache(maxsize=128)
    def get_user_from_db(self, _token: str, email: str) -> User | None:
        """
        Get the user from the database. This is a helper function to be used by the
        convert_to_user decorator. The function is cached to avoid repeated database
        queries. To scope the cache to the current request, the token and email are
        used as the cache key.

        Args:
            _token (str): The token
            email (str): The email
        """
        if not self.datasources:
            raise RuntimeError("Datasources not loaded")
        return self.datasources.mongodb.get_user_by_email(email)
