import asyncio
import inspect
import json
from typing import TYPE_CHECKING

import socketio
from bec_lib.endpoints import MessageEndpoints
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bec_atlas.router.base_router import BaseRouter

if TYPE_CHECKING:
    from bec_lib.redis_connector import RedisConnector


class RedisRouter(BaseRouter):
    """
    This class is a router for the Redis API. It exposes the redis client through
    the API. For pub/sub and stream operations, a websocket connection can be used.
    """

    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.redis = self.datasources.datasources["redis"].connector
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route("/redis", self.redis_get, methods=["GET"])
        self.router.add_api_route("/redis", self.redis_post, methods=["POST"])
        self.router.add_api_route("/redis", self.redis_delete, methods=["DELETE"])

    async def redis_get(self, key: str):
        return self.redis.get(key)

    async def redis_post(self, key: str, value: str):
        return self.redis.set(key, value)

    async def redis_delete(self, key: str):
        return self.redis.delete(key)


class RedisWebsocket:
    """
    This class is a websocket handler for the Redis API. It exposes the redis client through
    the websocket.
    """

    def __init__(self, prefix="/api/v1", datasources=None):
        self.redis: RedisConnector = datasources.datasources["redis"].connector
        self.prefix = prefix
        self.active_connections = set()
        self.socket = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")
        self.app = socketio.ASGIApp(self.socket)
        self.loop = asyncio.get_event_loop()

        self.socket.on("connect", self.connect_client)
        self.socket.on("register", self.redis_register)
        self.socket.on("disconnect", self.disconnect_client)

    def connect_client(self, sid, environ):
        print("Client connected")
        self.active_connections.add(sid)

    def disconnect_client(self, sid, _environ):
        print("Client disconnected")
        self.active_connections.pop(sid)

    async def redis_register(self, sid: str, msg: str):
        if sid not in self.active_connections:
            self.active_connections.add(sid)
        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            return

        endpoint = getattr(MessageEndpoints, data.get("endpoint"))

        # check if the endpoint receives arguments
        if len(inspect.signature(endpoint).parameters) > 1:
            endpoint = endpoint(data.get("args"))
        else:
            endpoint = endpoint()

        self.redis.register(endpoint, cb=self.on_redis_message, parent=self)
        await self.socket.enter_room(sid, endpoint.endpoint)
        await self.socket.emit("registered", data={"endpoint": endpoint.endpoint}, room=sid)

    @staticmethod
    def on_redis_message(message, parent):
        async def emit_message(message):
            outgoing = {
                "data": message.value.model_dump_json(),
                "message_type": message.value.__class__.__name__,
            }
            await parent.socket.emit("new_message", data=outgoing, room=message.topic)

        # check that the event loop is running
        if not parent.loop.is_running():
            parent.loop.run_until_complete(emit_message(message))
        else:
            asyncio.run_coroutine_threadsafe(emit_message(message), parent.loop)
