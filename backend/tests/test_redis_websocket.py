import json
from unittest import mock

import pytest
from bec_atlas.router.redis_router import RedisAtlasEndpoints
from bec_lib.endpoints import MessageEndpoints


@pytest.fixture
def backend_client(backend):
    client, app = backend
    app.server = mock.Mock()
    app.server.should_exit = False
    app.redis_websocket.users = {}
    yield client, app
    app.redis_websocket.redis._redis_conn.flushall()


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_websocket_connect(backend_client):
    client, app = backend_client
    await app.redis_websocket.socket.handlers["/"]["connect"](
        "sid", {"HTTP_QUERY": '{"user": "test", "deployment": "test"}'}
    )
    assert "sid" in app.redis_websocket.users


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_websocket_disconnect(backend_client):
    client, app = backend_client
    app.redis_websocket.users["sid"] = {"user": "test", "subscriptions": []}
    await app.redis_websocket.socket.handlers["/"]["disconnect"]("sid")
    assert "sid" not in app.redis_websocket.users


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_websocket_multiple_connect(backend_client):
    client, app = backend_client
    await app.redis_websocket.socket.handlers["/"]["connect"](
        "sid1", {"HTTP_QUERY": '{"user": "test", "deployment": "test"}'}
    )
    await app.redis_websocket.socket.handlers["/"]["connect"](
        "sid2", {"HTTP_QUERY": '{"user": "test", "deployment": "test"}'}
    )
    assert "sid1" in app.redis_websocket.users
    assert "sid2" in app.redis_websocket.users


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_websocket_multiple_connect_same_sid(backend_client):
    client, app = backend_client
    await app.redis_websocket.socket.handlers["/"]["connect"](
        "sid", {"HTTP_QUERY": '{"user": "test", "deployment": "test"}'}
    )
    await app.redis_websocket.socket.handlers["/"]["connect"](
        "sid", {"HTTP_QUERY": '{"user": "test", "deployment": "test"}'}
    )

    assert "sid" in app.redis_websocket.users
    assert len(app.redis_websocket.users) == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_websocket_multiple_disconnect_same_sid(backend_client):
    client, app = backend_client
    app.redis_websocket.users["sid"] = {"user": "test", "subscriptions": []}
    await app.redis_websocket.socket.handlers["/"]["disconnect"]("sid")
    await app.redis_websocket.socket.handlers["/"]["disconnect"]("sid")
    assert "sid" not in app.redis_websocket.users
    assert len(app.redis_websocket.users) == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_websocket_register_wrong_endpoint_raises(backend_client):
    client, app = backend_client
    with mock.patch.object(app.redis_websocket.socket, "emit") as emit:
        await app.redis_websocket.socket.handlers["/"]["connect"]("sid")
        await app.redis_websocket.socket.handlers["/"]["register"](
            "sid", json.dumps({"endpoint": "wrong_endpoint"})
        )
        assert mock.call("error", mock.ANY, room="sid") in emit.mock_calls


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_websocket_register(backend_client):
    client, app = backend_client
    with mock.patch.object(app.redis_websocket.socket, "emit") as emit:
        with mock.patch.object(app.redis_websocket.socket, "enter_room") as enter_room:
            await app.redis_websocket.socket.handlers["/"]["connect"](
                "sid", {"HTTP_QUERY": '{"user": "test", "deployment": "test"}'}
            )

            await app.redis_websocket.socket.handlers["/"]["register"](
                "sid", json.dumps({"endpoint": "scan_status"})
            )
            assert mock.call("error", mock.ANY, room="sid") not in emit.mock_calls
            enter_room.assert_called_with(
                "sid",
                RedisAtlasEndpoints.socketio_endpoint_room(
                    "test", MessageEndpoints.scan_status().endpoint
                ),
            )

            assert mock.call("error", mock.ANY, room="sid") not in emit.mock_calls
