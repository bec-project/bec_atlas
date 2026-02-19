import asyncio
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


class TestRedis(fakeredis.FakeAsyncRedis):
    async def execute_command(self, *args, **options):
        return await asyncio.shield(super().execute_command(*args, **options))


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
        "messaging_services",
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

    def _fake_redis(host, port, **kwargs):
        return fakeredis.FakeStrictRedis(server=redis_server)

    mongo_client = mongomock.MongoClient("localhost", 27027)
    fake_async_redis = TestRedis(server=redis_server, username="ingestor", password="ingestor")
    fake_async_redis.connection_pool.connection_kwargs["username"] = "ingestor"
    fake_async_redis.connection_pool.connection_kwargs["password"] = "ingestor"

    config = {
        "redis": {
            "host": "localhost",
            "port": 6480,
            "username": "ingestor",
            "password": "ingestor",
            "sync_instance": RedisConnector("localhost:1", redis_cls=_fake_redis),
            "async_instance": fake_async_redis,
        },
        "mongodb": {"host": "localhost", "port": 27027, "mongodb_client": mongo_client},
        "scilog": {"username": "test_user", "password": "test_password"},
        "signal": {"host": "http://localhost:8080", "number": "+1234567890"},
    }

    import_mongodb_data(mongo_client)

    with mock.patch("bec_atlas.ingestor.scilog_logbook_manager.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"token": "test_token"}
        app = AtlasApp(config)

    class PatchedBECAsyncRedisManager(BECAsyncRedisManager):
        def _redis_connect(self):
            self.redis = fake_async_redis
            self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
            self.connected = True

    with mock.patch(
        "bec_atlas.router.redis_router.BECAsyncRedisManager", PatchedBECAsyncRedisManager
    ):
        with TestClient(app.app) as _client:
            app.user_router.use_ssl = False  # disable ssl to allow for httponly cookies
            yield _client, app


@pytest.fixture
def logged_in_client(backend):
    client, _ = backend
    response = client.post(
        "/api/v1/user/login", json={"username": "admin@bec_atlas.ch", "password": "admin"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert isinstance(token, str)
    assert len(token) > 20
    return client


@pytest.fixture
def mock_sse_response():
    """
    Create a factory for SSE (Server-Sent Events) mock responses.

    Returns a factory function that accepts an iterable of SSE lines and returns
    a configured mock response suitable for streaming endpoints.

    Usage:
        def test_something(mock_sse_response):
            response = mock_sse_response(iter(["data: {}", "data: {}"]))
            with mock.patch("requests.get", return_value=response):
                # test code
    """

    def _create_mock_response(lines_iterable):
        """Create a mock response with the given SSE lines."""
        mock_response = mock.Mock()
        mock_response.raise_for_status = mock.Mock()
        mock_response.encoding = "utf-8"
        mock_response.iter_lines = mock.Mock(return_value=lines_iterable)
        mock_response.__enter__ = mock.Mock(return_value=mock_response)
        mock_response.__exit__ = mock.Mock(return_value=False)
        return mock_response

    return _create_mock_response


@pytest.fixture
def mock_http_response():
    """
    Create a factory for standard HTTP mock responses.

    Returns a factory function that accepts a response body (dict/list) and returns
    a configured mock response with a json() method.

    Usage:
        def test_something(mock_http_response):
            response = mock_http_response({"key": "value"})
            with mock.patch("requests.get", return_value=response):
                # test code
    """

    def _create_mock_response(json_data, status_code=200):
        """Create a mock response with the given JSON data."""
        mock_response = mock.Mock()
        mock_response.json.return_value = json_data
        mock_response.status_code = status_code
        mock_response.raise_for_status = mock.Mock()
        return mock_response

    return _create_mock_response
