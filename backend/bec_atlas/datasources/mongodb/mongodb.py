import json
import os

import pymongo
from bec_lib.logger import bec_logger
from pydantic import BaseModel

from bec_atlas.authentication import get_password_hash
from bec_atlas.model.model import User, UserCredentials

logger = bec_logger.logger


class MongoDBDatasource:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.client = None
        self.db = None

    def connect(self, include_setup: bool = True):
        """
        Connect to the MongoDB database.
        """
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 27017)
        logger.info(f"Connecting to MongoDB at {host}:{port}")
        self.client = pymongo.MongoClient(f"mongodb://{host}:{port}/")
        self.db = self.client["bec_atlas"]
        if include_setup:
            self.db["users"].create_index([("email", 1)], unique=True)
            self.load_functional_accounts()

    def load_functional_accounts(self):
        """
        Load the functional accounts to the database.
        """
        functional_accounts_file = os.path.join(
            os.path.dirname(__file__), "functional_accounts.json"
        )
        if os.path.exists(functional_accounts_file):
            with open(functional_accounts_file, "r", encoding="utf-8") as file:
                functional_accounts = json.load(file)
        else:
            print("Functional accounts file not found. Using default demo accounts.")
            # Demo accounts
            functional_accounts = [
                {
                    "email": "admin@bec_atlas.ch",
                    "password": "admin",
                    "groups": ["demo", "admin"],
                    "first_name": "Admin",
                    "last_name": "Admin",
                    "owner_groups": ["admin"],
                },
                {
                    "email": "jane.doe@bec_atlas.ch",
                    "password": "atlas",
                    "groups": ["demo_user"],
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "owner_groups": ["admin"],
                },
            ]

        for account in functional_accounts:
            # check if the account already exists in the database
            password = account.pop("password")
            password_hash = get_password_hash(password)
            result = self.db["users"].find_one({"email": account["email"]})
            if result is not None:
                continue
            user = User(**account)
            user = self.db["users"].insert_one(user.__dict__)
            credentials = UserCredentials(
                owner_groups=["admin"], user_id=user.inserted_id, password=password_hash
            )
            self.db["user_credentials"].insert_one(credentials.__dict__)

    def get_user_by_email(self, email: str) -> User | None:
        """
        Get the user from the database.
        """
        out = self.db["users"].find_one({"email": email})
        if out is None:
            return None
        return User(**out)

    def get_user_credentials(self, user_id: str) -> UserCredentials | None:
        """
        Get the user credentials from the database.
        """
        out = self.db["user_credentials"].find_one({"user_id": user_id})
        if out is None:
            return None
        return UserCredentials(**out)

    def find_one(
        self, collection: str, query_filter: dict, dtype: BaseModel, user: User | None = None
    ) -> BaseModel | None:
        """
        Find one document in the collection.

        Args:
            collection (str): The collection name
            query_filter (dict): The filter to apply
            dtype (BaseModel): The data type to return
            user (User): The user making the request

        Returns:
            BaseModel: The data type with the document data
        """
        if user is not None:
            query_filter = self.add_user_filter(user, query_filter)
        out = self.db[collection].find_one(query_filter)
        if out is None:
            return None
        return dtype(**out)

    def find(
        self, collection: str, query_filter: dict, dtype: BaseModel, user: User | None = None
    ) -> list[BaseModel]:
        """
        Find all documents in the collection.

        Args:
            collection (str): The collection name
            query_filter (dict): The filter to apply
            dtype (BaseModel): The data type to return
            user (User): The user making the request

        Returns:
            list[BaseModel]: The data type with the document data
        """
        if user is not None:
            query_filter = self.add_user_filter(user, query_filter)
        out = self.db[collection].find(query_filter)
        return [dtype(**x) for x in out]

    def add_user_filter(self, user: User, query_filter: dict) -> dict:
        """
        Add the user filter to the query filter.

        Args:
            user (User): The user making the request
            query_filter (dict): The query filter

        Returns:
            dict: The updated query filter
        """
        if "admin" not in user.groups:
            query_filter = {
                "$and": [
                    query_filter,
                    {
                        "$or": [
                            {"owner_groups": {"$in": user.groups}},
                            {"access_groups": {"$in": user.groups}},
                        ]
                    },
                ]
            }
        return query_filter

    def shutdown(self):
        """
        Shutdown the connection to the database.
        """
        if self.client is not None:
            self.client.close()
            logger.info("Connection to MongoDB closed.")
