import asyncio
import functools
import inspect
import json
import traceback
from typing import TYPE_CHECKING

import socketio
from bec_lib.endpoints import MessageEndpoints
from bec_lib.logger import bec_logger
from fastapi import APIRouter

from bec_atlas.router.base_router import BaseRouter

logger = bec_logger.logger

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


def safe_socket(fcn):
    @functools.wraps(fcn)
    async def wrapper(self, sid, *args, **kwargs):
        try:
            out = await fcn(self, sid, *args, **kwargs)
        except Exception as exc:
            content = traceback.format_exc()
            logger.error(content)
            await self.socket.emit("error", {"error": str(exc)}, room=sid)
            return
        return out

    return wrapper


class BECAsyncRedisManager(socketio.AsyncRedisManager):
    def __init__(
        self,
        parent,
        url="redis://localhost:6379/0",
        channel="socketio",
        write_only=False,
        logger=None,
        redis_options=None,
    ):
        self.parent = parent
        super().__init__(url, channel, write_only, logger, redis_options)
        self.requested_channels = []
        self.started_update_loop = False

        # task = asyncio.create_task(self._required_channel_heartbeat())
        # loop.run_until_complete(task)

    def start_update_loop(self):
        self.started_update_loop = True
        loop = asyncio.get_event_loop()
        task = loop.create_task(self._backend_heartbeat())
        return task

    async def disconnect(self, sid, namespace, **kwargs):
        if kwargs.get("ignore_queue"):
            await super().disconnect(sid, namespace, **kwargs)
            await self.update_state_info()
            return
        message = {
            "method": "disconnect",
            "sid": sid,
            "namespace": namespace or "/",
            "host_id": self.host_id,
        }
        await self._handle_disconnect(message)  # handle in this host
        await self._publish(message)  # notify other hosts

    async def enter_room(self, sid, namespace, room, eio_sid=None):
        await super().enter_room(sid, namespace, room, eio_sid=eio_sid)
        await self.update_state_info()

    async def leave_room(self, sid, namespace, room):
        await super().leave_room(sid, namespace, room)
        await self.update_state_info()

    async def _backend_heartbeat(self):
        while not self.parent.fastapi_app.server.should_exit:
            await asyncio.sleep(1)
            await self.redis.publish(f"deployments/{self.host_id}/heartbeat/", "ping")
            data = json.dumps(self.parent.users)
            print(f"Sending heartbeat: {data}")
            await self.redis.set(f"deployments/{self.host_id}/state/", data, ex=30)

    async def update_state_info(self):
        data = json.dumps(self.parent.users)
        await self.redis.set(f"deployments/{self.host_id}/state/", data, ex=30)
        await self.redis.publish(f"deployments/{self.host_id}/state/", data)

    async def update_websocket_states(self):
        loop = asyncio.get_event_loop()
        if not self.started_update_loop and loop.is_running():
            self.start_update_loop()
        await self.update_state_info()

    async def remove_user(self, sid):
        if sid in self.parent.users:
            del self.parent.users[sid]
        print(f"Removed user {sid}")
        await self.update_state_info()


class RedisWebsocket:
    """
    This class is a websocket handler for the Redis API. It exposes the redis client through
    the websocket.
    """

    def __init__(self, prefix="/api/v1", datasources=None, app=None):
        self.redis: RedisConnector = datasources.datasources["redis"].connector
        self.prefix = prefix
        self.fastapi_app = app
        self.active_connections = set()
        self.socket = socketio.AsyncServer(
            cors_allowed_origins="*",
            async_mode="asgi",
            client_manager=BECAsyncRedisManager(
                self, url=f"redis://{self.redis.host}:{self.redis.port}/0"
            ),
        )
        self.app = socketio.ASGIApp(self.socket)
        self.loop = asyncio.get_event_loop()
        self.users = {}

        self.socket.on("connect", self.connect_client)
        self.socket.on("register", self.redis_register)
        self.socket.on("unregister", self.redis.unregister)
        self.socket.on("disconnect", self.disconnect_client)

    @safe_socket
    async def connect_client(self, sid, environ=None):
        print("Client connected")
        http_query = environ.get("HTTP_QUERY")
        if not http_query:
            raise ValueError("Query parameters not found")
        query = json.loads(http_query)

        if "user" not in query:
            raise ValueError("User not found in query parameters")
        user = query["user"]

        if sid not in self.users:
            # check if the user was already registered in redis
            deployment_keys = await self.socket.manager.redis.keys("deployments/*/state/")
            if not deployment_keys:
                state_data = []
            else:
                state_data = await self.socket.manager.redis.mget(*deployment_keys)
            info = {}
            for data in state_data:
                if not data:
                    continue
                obj = json.loads(data)
                for value in obj.values():
                    info[value["user"]] = value["subscriptions"]

            if user in info:
                self.users[sid] = {"user": user, "subscriptions": info[user]}
                for endpoint in set(self.users[sid]["subscriptions"]):
                    await self.socket.enter_room(sid, f"ENDPOINT::{endpoint}")
                await self.socket.manager.update_websocket_states()
            else:
                self.users[sid] = {"user": query["user"], "subscriptions": []}

        await self.socket.manager.update_websocket_states()

    async def disconnect_client(self, sid, _environ=None):
        print("Client disconnected")
        is_exit = self.fastapi_app.server.should_exit
        if is_exit:
            return
        await self.socket.manager.remove_user(sid)

    @safe_socket
    async def redis_register(self, sid: str, msg: str):
        """
        Register a client to a redis channel.

        Args:
            sid (str): The socket id of the client
            msg (str): The message sent by the client
        """
        if sid not in self.active_connections:
            self.active_connections.add(sid)
        try:
            print(msg)
            data = json.loads(msg)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON message")

        endpoint = getattr(MessageEndpoints, data.get("endpoint"), None)
        if endpoint is None:
            raise ValueError(f"Endpoint {data.get('endpoint')} not found")

        # check if the endpoint receives arguments
        if len(inspect.signature(endpoint).parameters) > 0:
            endpoint = endpoint(data.get("args"))
        else:
            endpoint = endpoint()

        self.redis.register(endpoint, cb=self.on_redis_message, parent=self)
        if data.get("endpoint") not in self.users[sid]["subscriptions"]:
            await self.socket.enter_room(sid, f"ENDPOINT::{data.get('endpoint')}")
            self.users[sid]["subscriptions"].append(data.get("endpoint"))
            await self.socket.manager.update_websocket_states()

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
