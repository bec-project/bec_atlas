from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Literal, Type, TypeVar

import pymongo
from bec_lib.logger import bec_logger
from pydantic import BaseModel

from bec_atlas.authentication import get_password_hash
from bec_atlas.model.model import User, UserCredentials

logger = bec_logger.logger

if TYPE_CHECKING:
    from bson import ObjectId

T = TypeVar("T", bound=BaseModel)


class MongoDBDatasource:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.client = None
        self.db = None

    def connect(self, include_setup: bool = True):
        """
        Connect to the MongoDB database.
        """
        host = self.config.get("host")
        port = self.config.get("port")
        username = self.config.get("username")
        password = self.config.get("password")
        if username and password:
            self.client = pymongo.MongoClient(
                f"mongodb://{username}:{password}@{host}:{port}/?authSource=bec_atlas"
            )
        else:
            self.client = pymongo.MongoClient(f"mongodb://{host}:{port}/")

        # Check if the connection is successful
        self.client.list_databases()

        logger.info(f"Connecting to MongoDB at {host}:{port}")
        self.db = self.client["bec_atlas"]
        if include_setup:
            self.db["users"].create_index([("email", 1)], unique=True)
            self.load_functional_accounts()

    def load_functional_accounts(self):
        """
        Load the functional accounts to the database.
        """
        functional_accounts_file = os.path.join(
            os.path.dirname(__file__), ".functional_accounts.json"
        )
        if not os.path.exists(functional_accounts_file):
            raise FileNotFoundError(
                f"Could not find functional accounts file at {functional_accounts_file}"
            )

        with open(functional_accounts_file, "r", encoding="utf-8") as file:
            functional_accounts = json.load(file)
        for account in functional_accounts:
            account["groups"].append("atlas_func_account")
            account = list(set(account["groups"]))

        existing_accounts = list(
            self.db["users"].find({"groups": {"$in": ["atlas_func_account"]}}, {"email": 1})
        )

        for account in functional_accounts:
            # check if the account already exists in the database
            password = account.pop("password")
            password_hash = get_password_hash(password)

            result = None
            for existing_account in existing_accounts:
                if existing_account["email"] == account["email"]:
                    result = existing_account
                    existing_accounts.remove(existing_account)
                    break
            if result is not None:
                # account already exists; check if the password is the same
                credentials = self.db["user_credentials"].find_one({"user_id": result["_id"]})
                if credentials is not None and credentials["password"] == password_hash:
                    continue
                # update the password
                self.db["user_credentials"].update_one(
                    {"user_id": result["_id"]}, {"$set": {"password": password_hash}}
                )
                continue
            user = User(**account)
            user = self.db["users"].insert_one(user.__dict__)
            credentials = UserCredentials(
                owner_groups=["admin"], user_id=user.inserted_id, password=password_hash
            )
            self.db["user_credentials"].insert_one(credentials.__dict__)

        # remove any accounts that are no longer in the functional accounts file
        for account in existing_accounts:
            self.db["users"].delete_one({"_id": account["_id"]})
            self.db["user_credentials"].delete_one({"user_id": account["_id"]})

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
        self,
        collection: str,
        query_filter: dict,
        dtype: Type[T],
        fields: list[str] = None,
        user: User | None = None,
    ) -> T | None:
        """
        Find one document in the collection.

        Args:
            collection (str): The collection name
            query_filter (dict): The filter to apply
            dtype (Type[T]): The data type to return
            user (User): The user making the request

        Returns:
            T: The data type with the document data
        """
        if user is not None:
            query_filter = self.add_user_filter(user, query_filter)
        out = self.db[collection].find_one(query_filter, projection=fields)
        if out is None:
            return None
        return dtype(**out)

    def find(
        self,
        collection: str,
        query_filter: dict,
        dtype: Type[T],
        limit: int = 0,
        offset: int = 0,
        fields: list[str] = None,
        sort: list[str] = None,
        user: User | None = None,
    ) -> list[T]:
        """
        Find all documents in the collection.

        Args:
            collection (str): The collection name
            query_filter (dict): The filter to apply
            dtype (Type[T]): The data type to return
            user (User): The user making the request

        Returns:
            list[BaseModel]: The data type with the document data
        """
        if user is not None:
            query_filter = self.add_user_filter(user, query_filter)
        out = self.db[collection].find(
            query_filter, limit=limit, skip=offset, projection=fields, sort=sort
        )
        return [dtype(**x) for x in out]

    def post(self, collection: str, data: dict, dtype: Type[T], user: User | None = None) -> T:
        """
        Post a single document to the collection.

        Args:
            collection (str): The collection name
            data (dict): The data to insert
            dtype (Type[T]): The data type to return
            user (User): The user making the request

        Returns:
            T: The data type with the document data
        """
        if user is not None:
            data = self.add_user_filter(user, data, operation="w")
        out = self.db[collection].insert_one(data)
        return dtype(**data)

    def patch(
        self,
        collection: str,
        id: ObjectId,
        update: dict,
        dtype: Type[T],
        user: User | None = None,
        return_document: bool = True,
    ) -> T | None:
        """
        Patch a single document in the collection.

        Args:
            collection (str): The collection name
            id (ObjectId): The document id
            update (dict): The update to apply
            dtype (Type[T]): The data type to return
            user (User): The user making the request
            return_document (bool): When True, return the updated document, otherwise return the original document

        Returns:
            Type[T]: The data type with the document data
        """
        search_filter = {"_id": id}
        if user is not None:
            search_filter = self.add_user_filter(user, search_filter, operation="w")
        out = self.db[collection].find_one_and_update(
            filter=search_filter, update={"$set": update}, return_document=return_document
        )
        if out is None:
            return None
        return dtype(**out)

    def delete_one(self, collection: str, filter: dict, user: User | None = None) -> bool:
        """
        Delete a single document in the collection.

        Args:
            collection (str): The collection name
            filter (dict): The filter to apply
            user (User): The user making the request

        Returns:
            bool: True if the document was deleted, otherwise False
        """
        if user is not None:
            filter = self.add_user_filter(user, filter, operation="w")
        out = self.db[collection].delete_one(filter)
        return out.deleted_count > 0

    def aggregate(
        self, collection: str, pipeline: list[dict], dtype: Type[T], user: User | None = None
    ) -> list[T]:
        """
        Aggregate documents in the collection.

        Args:
            collection (str): The collection name
            pipeline (list[dict]): The aggregation pipeline
            dtype (Type[T]): The data type to return
            user (User): The user making the request

        Returns:
            list[T]: The data type with the document data
        """
        if user is not None:
            # Add the user filter to the lookup pipeline

            for pipe in pipeline:
                if "$lookup" not in pipe:
                    continue
                if "pipeline" not in pipe["$lookup"]:
                    continue
                lookup = pipe["$lookup"]
                lookup_pipeline = lookup["pipeline"]
                access_filter = {"$match": self._read_only_user_filter(user)}
                lookup_pipeline.insert(0, access_filter)
            # pipeline = self.add_user_filter(user, pipeline)

        out = self.db[collection].aggregate(pipeline)
        if dtype is None:
            return list(out)
        return [dtype(**x) for x in out]

    def add_user_filter(
        self, user: User, query_filter: dict, operation: Literal["r", "w"] = "r"
    ) -> dict:
        """
        Add the user filter to the query filter.

        Args:
            user (User): The user making the request
            query_filter (dict): The query filter
            operation (Literal["r", "w"]): The operation to perform

        Returns:
            dict: The updated query filter
        """
        if operation == "r":
            user_filter = self._read_only_user_filter(user)
        else:
            user_filter = self._write_user_filter(user)
        if user_filter:
            query_filter = {"$and": [query_filter, user_filter]}
        return query_filter

    def _read_only_user_filter(self, user: User) -> dict:
        """
        Add the user filter to the query filter.

        Args:
            user (User): The user making the request

        Returns:
            dict: The updated query filter
        """
        if "admin" not in user.groups:
            return {
                "$or": [
                    {"owner_groups": {"$in": user.groups}},
                    {"access_groups": {"$in": user.groups}},
                ]
            }
        return {}

    def _write_user_filter(self, user: User) -> dict:
        """
        Add the user filter to the query filter.

        Args:
            user (User): The user making the request

        Returns:
            dict: The updated query filter
        """
        if "admin" not in user.groups:
            return {"$or": [{"owner_groups": {"$in": user.groups}}]}
        return {}

    def shutdown(self):
        """
        Shutdown the connection to the database.
        """
        if self.client is not None:
            self.client.close()
            logger.info("Connection to MongoDB closed.")
