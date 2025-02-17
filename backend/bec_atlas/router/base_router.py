from functools import lru_cache

from bec_atlas.model.model import User


class BaseRouter:
    def __init__(self, prefix: str = "/api/v1", datasources=None) -> None:
        self.datasources = datasources
        self.prefix = prefix

    @lru_cache(maxsize=128)
    def get_user_from_db(self, _token: str, email: str) -> User:
        """
        Get the user from the database. This is a helper function to be used by the
        convert_to_user decorator. The function is cached to avoid repeated database
        queries. To scope the cache to the current request, the token and email are
        used as the cache key.

        Args:
            _token (str): The token
            email (str): The email
        """
        return self.datasources.datasources["mongodb"].get_user_by_email(email)
