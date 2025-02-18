import json
from unittest import mock

import pytest
from bec_lib.endpoints import MessageEndpoints

from bec_atlas.router.redis_router import RedisAtlasEndpoints, RemoteAccess


@pytest.fixture
def backend_client(backend):
    client, app = backend
    app.server = mock.Mock()
    app.server.should_exit = False
    app.redis_websocket.users = {}
    response = client.post(
        "/api/v1/user/login", json={"username": "admin@bec_atlas.ch", "password": "admin"}
    )
    assert response.status_code == 200
    token = response.json()
    assert isinstance(token, str)
    assert len(token) > 20
    return client, app


@pytest.fixture
@pytest.mark.asyncio(loop_scope="session")
async def connected_ws(backend_client):
    client, app = backend_client
    deployment = client.get("/api/v1/deployments/realm", params={"realm": "demo_beamline_1"}).json()
    with mock.patch.object(app.redis_router, "get_access", return_value=RemoteAccess.READ):
        await app.redis_websocket.socket.handlers["/"]["connect"](
            "sid",
            {
                "HTTP_QUERY": json.dumps({"deployment": deployment[0]["_id"]}),
                "HTTP_COOKIE": f"access_token={client.cookies.get('access_token')}",
            },
        )
        yield backend_client


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_websocket_connect(connected_ws):
    _, app = await anext(connected_ws)
    assert "sid" in app.redis_websocket.users


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_websocket_disconnect(connected_ws):
    _, app = await anext(connected_ws)
    await app.redis_websocket.socket.handlers["/"]["disconnect"]("sid")
    assert "sid" not in app.redis_websocket.users


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_websocket_multiple_connect(connected_ws):
    client, app = await anext(connected_ws)

    await app.redis_websocket.socket.handlers["/"]["connect"](
        "sid2",
        {
            "HTTP_QUERY": json.dumps(
                {"deployment": app.redis_websocket.users["sid"]["deployment"]}
            ),
            "HTTP_COOKIE": f"access_token={client.cookies.get('access_token')}",
        },
    )

    assert "sid" in app.redis_websocket.users
    assert "sid2" in app.redis_websocket.users


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_websocket_multiple_connect_same_sid(connected_ws):
    client, app = await anext(connected_ws)

    await app.redis_websocket.socket.handlers["/"]["connect"](
        "sid",
        {
            "HTTP_QUERY": json.dumps(
                {"deployment": app.redis_websocket.users["sid"]["deployment"]}
            ),
            "HTTP_COOKIE": f"access_token={client.cookies.get('access_token')}",
        },
    )

    assert "sid" in app.redis_websocket.users
    assert len(app.redis_websocket.users) == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_websocket_multiple_disconnect_same_sid(connected_ws):
    client, app = await anext(connected_ws)
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
async def test_redis_websocket_register(connected_ws):
    client, app = await anext(connected_ws)
    with mock.patch.object(app.redis_websocket.socket, "emit") as emit:
        with mock.patch.object(app.redis_websocket.socket, "enter_room") as enter_room:
            await app.redis_websocket.socket.handlers["/"]["register"](
                "sid", json.dumps({"endpoint": "scan_status"})
            )
            assert mock.call("error", mock.ANY, room="sid") not in emit.mock_calls
            enter_room.assert_called_with(
                "sid",
                RedisAtlasEndpoints.socketio_endpoint_room(
                    app.redis_websocket.users["sid"]["deployment"],
                    MessageEndpoints.scan_status().endpoint,
                ),
            )

            assert mock.call("error", mock.ANY, room="sid") not in emit.mock_calls
