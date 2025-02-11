import json
import os
from unittest import mock

import fakeredis
import mongomock
import pymongo
import pytest
from bec_lib.redis_connector import RedisConnector
from bson import ObjectId
from fastapi.testclient import TestClient

from bec_atlas.main import AtlasApp
from bec_atlas.router.redis_router import BECAsyncRedisManager


def import_mongodb_data(mongo_client: pymongo.MongoClient):
    """
    Import the test data into the mongodb container. The data is stored in the
    tests/test_data directory as json files per collection.

    Args:
        mongo_client (pymongo.MongoClient): The mongo client
    """
    client = mongo_client
    db = client["bec_atlas"]

    collections = [
        # "bec_access_profiles",
        "deployment_access",
        "deployment_credentials",
        "deployments",
        # "fs.chunks",
        # "fs.files",
        "scans",
        "sessions",
        "user_credentials",
        "users",
    ]

    for collection in collections:
        db.drop_collection(collection)

    current_dir = os.path.dirname(os.path.abspath(__file__))

    for collection in collections:
        with open(
            f"{current_dir}/test_data/bec_atlas.{collection}.json", "r", encoding="utf-8"
        ) as f:
            data = f.read()
            data = json.loads(data)
            data = [convert_to_object_id(d) for d in data]

            db[collection].insert_many(data)
    client.close()


def convert_to_object_id(data):
    """
    Convert the _id field in the data to an ObjectId.

    Args:
        data (dict): The data

    Returns:
        dict: The data with the _id field converted to an ObjectId
    """
    if isinstance(data, dict) and "$oid" in data:
        return ObjectId(data["$oid"])
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = convert_to_object_id(value)
    return data


@pytest.fixture()
def redis_server():
    redis_server = fakeredis.FakeServer()
    yield redis_server


@pytest.fixture()
def backend(redis_server):

    def _fake_redis(host, port):
        return fakeredis.FakeStrictRedis(server=redis_server)

    mongo_client = mongomock.MongoClient("localhost", 27027)

    config = {
        "redis": {
            "host": "localhost",
            "port": 6480,
            "username": "ingestor",
            "password": "ingestor",
            "sync_instance": RedisConnector("localhost:1", redis_cls=_fake_redis),
            "async_instance": fakeredis.FakeAsyncRedis(server=redis_server),
        },
        "mongodb": {"host": "localhost", "port": 27027, "mongodb_client": mongo_client},
    }

    import_mongodb_data(mongo_client)

    app = AtlasApp(config)

    class PatchedBECAsyncRedisManager(BECAsyncRedisManager):
        def _redis_connect(self):
            self.redis = fakeredis.FakeAsyncRedis(
                server=redis_server,
                username=config["redis"]["username"],
                password=config["redis"]["password"],
            )
            self.redis.connection_pool.connection_kwargs["username"] = config["redis"]["username"]
            self.redis.connection_pool.connection_kwargs["password"] = config["redis"]["password"]
            self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)

    with mock.patch(
        "bec_atlas.router.redis_router.BECAsyncRedisManager", PatchedBECAsyncRedisManager
    ):
        with TestClient(app.app) as _client:
            yield _client, app
