import asyncio
import functools
import inspect
import json
import traceback
import uuid
from typing import TYPE_CHECKING, Any

import socketio
from bec_lib.endpoints import EndpointInfo, MessageEndpoints, MessageOp
from bec_lib.logger import bec_logger
from bec_lib.serialization import MsgpackSerialization, json_ext
from fastapi import APIRouter, Query, Response

from bec_atlas.router.base_router import BaseRouter

logger = bec_logger.logger

if TYPE_CHECKING:
    from bec_lib.redis_connector import RedisConnector


class RedisAtlasEndpoints:
    """
    This class contains the endpoints for the Redis API. It is used to
    manage the subscriptions and the state information for the websocket
    """

    @staticmethod
    def websocket_state(deployment: str, host_id: str):
        """
        Endpoint for the websocket state information, containing the users and their subscriptions
        per backend host.

        Args:
            deployment (str): The deployment name
            host_id (str): The host id of the backend

        Returns:
            str: The endpoint for the websocket state information
        """
        return f"internal/deployment/{deployment}/{host_id}/state"

    @staticmethod
    def redis_data(deployment: str, endpoint: str):
        """
        Endpoint for the redis data for a deployment and endpoint.

        Args:
            deployment (str): The deployment name
            endpoint (str): The endpoint name

        Returns:
            str: The endpoint for the redis data
        """
        return f"internal/deployment/{deployment}/data/{endpoint}"

    @staticmethod
    def socketio_endpoint_room(deployment: str, endpoint: str):
        """
        Endpoint for the socketio room for an endpoint.

        Args:
            endpoint (str): The endpoint name

        Returns:
            str: The endpoint for the socketio room
        """
        return f"socketio/rooms/{deployment}/{endpoint}"

    @staticmethod
    def redis_request(deployment: str):
        """
        Endpoint for the redis request for a deployment and endpoint.

        Args:
            deployment (str): The deployment name

        Returns:
            str: The endpoint for the redis request
        """
        return f"internal/deployment/{deployment}/request"

    @staticmethod
    def redis_request_response(deployment: str, request_id: str):
        """
        Endpoint for the redis request response for a deployment and endpoint.

        Args:
            deployment (str): The deployment name
            request_id (str): The request id

        Returns:
            str: The endpoint for the redis request response
        """
        return f"internal/deployment/{deployment}/request_response/{request_id}"

    @staticmethod
    def redis_bec_acl_user(deployment_id: str):
        """
        Endpoint for the redis BEC ACL user for a deployment.

        Args:
            deployment_id (str): The deployment id

        Returns:
            str: The endpoint for the redis BEC ACL user
        """
        return f"internal/deployment/{deployment_id}/bec_access"


class MsgResponse(Response):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return content.encode()


class RedisRouter(BaseRouter):
    """
    This class is a router for the Redis API. It exposes the redis client through
    the API. For pub/sub and stream operations, a websocket connection can be used.
    """

    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.redis = self.datasources.datasources["redis"].async_connector

        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/redis", self.redis_get, methods=["GET"], response_class=MsgResponse
        )
        self.router.add_api_route("/redis", self.redis_post, methods=["POST"])
        self.router.add_api_route("/redis", self.redis_delete, methods=["DELETE"])

    async def redis_get(self, deployment: str, key: str = Query(...)):
        request_id = uuid.uuid4().hex
        response_endpoint = RedisAtlasEndpoints.redis_request_response(deployment, request_id)
        request_endpoint = RedisAtlasEndpoints.redis_request(deployment)
        pubsub = self.redis.pubsub()
        pubsub.ignore_subscribe_messages = True
        await pubsub.subscribe(response_endpoint)
        data = {"action": "get", "key": key, "response_endpoint": response_endpoint}
        await self.redis.publish(request_endpoint, json.dumps(data))
        response = await pubsub.get_message(timeout=10)
        print(response)
        response = await pubsub.get_message(timeout=10)
        out = MsgpackSerialization.loads(response["data"])

        return json_ext.dumps({"data": out.content, "metadata": out.metadata})

    async def redis_post(self, key: str, value: str):
        return self.redis.set(key, value)

    async def redis_delete(self, key: str):
        return self.redis.delete(key)


def safe_socket(fcn):
    @functools.wraps(fcn)
    async def wrapper(self, sid, *args, **kwargs):
        try:
            out = await fcn(self, sid, *args, **kwargs)
        # pylint: disable=broad-except
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
        self.known_deployments = set()

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
            await asyncio.sleep(10)
            await self.update_state_info()

    async def update_state_info(self):
        deployments = {deployment: {} for deployment in self.known_deployments}
        for user in self.parent.users:
            deployment = self.parent.users[user]["deployment"]
            if deployment not in deployments:
                deployments[deployment] = {}
                self.known_deployments.add(deployment)
            deployments[deployment][user] = self.parent.users[user]
        for name, data in deployments.items():
            data_json = json.dumps(data)
            await self.redis.set(
                RedisAtlasEndpoints.websocket_state(name, self.host_id), data_json, ex=30
            )
            await self.redis.publish(
                RedisAtlasEndpoints.websocket_state(name, self.host_id), data_json
            )

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
        redis_host = datasources.datasources["redis"].config["host"]
        redis_port = datasources.datasources["redis"].config["port"]
        redis_password = datasources.datasources["redis"].config.get("password", "ingestor")
        self.socket = socketio.AsyncServer(
            transports=["websocket"],
            ping_timeout=60,
            cors_allowed_origins="*",
            async_mode="asgi",
            client_manager=BECAsyncRedisManager(
                self,
                url=f"redis://{redis_host}:{redis_port}/0",
                redis_options={"username": "ingestor", "password": redis_password},
            ),
        )
        self.app = socketio.ASGIApp(self.socket, socketio_path=f"{prefix}/ws")
        self.loop = asyncio.get_event_loop()
        self.users = {}

        self.socket.on("connect", self.connect_client)
        self.socket.on("register", self.redis_register)
        self.socket.on("unregister", self.redis.unregister)
        self.socket.on("disconnect", self.disconnect_client)
        print("Redis websocket started")

    def _validate_new_user(self, http_query: str | None):
        """
        Validate the connection of a new user. In particular,
        the user must provide a valid token as well as have access
        to the deployment. If subscriptions are provided, the user
        must have access to the endpoints.

        Args:
            http_query (str): The query parameters of the websocket connection

        Returns:
            str: The user name

        """
        if not http_query:
            raise ValueError("Query parameters not found")
        if isinstance(http_query, str):
            query = json.loads(http_query)
        else:
            query = http_query

        if "user" not in query:
            raise ValueError("User not found in query parameters")
        user = query["user"]

        # TODO: Validate the user token

        deployment = query.get("deployment")
        if not deployment:
            raise ValueError("Deployment not found in query parameters")

        # TODO: Validate the user has access to the deployment

        return user, deployment

    @safe_socket
    async def connect_client(self, sid, environ=None, auth=None, **kwargs):
        if sid in self.users:
            logger.info("User already connected")
            return

        http_query = environ.get("HTTP_QUERY") or auth

        user, deployment = self._validate_new_user(http_query)

        # check if the user was already registered in redis
        socketio_server_keys = await self.socket.manager.redis.keys(
            RedisAtlasEndpoints.websocket_state(deployment, "*")
        )
        if not socketio_server_keys:
            state_data = []
        else:
            state_data = await self.socket.manager.redis.mget(*socketio_server_keys)
        info = {}
        for data in state_data:
            if not data:
                continue
            obj = json.loads(data)
            for value in obj.values():
                info[value["user"]] = value["subscriptions"]

        if user in info:
            self.users[sid] = {"user": user, "subscriptions": [], "deployment": deployment}
            for endpoint, endpoint_request in info[user]:
                print(f"Registering {endpoint}")
                await self._update_user_subscriptions(sid, endpoint, endpoint_request)
        else:
            self.users[sid] = {"user": user, "subscriptions": [], "deployment": deployment}

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
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON message") from exc

        endpoint = getattr(MessageEndpoints, data.get("endpoint"), None)
        if endpoint is None:
            raise ValueError(f"Endpoint {data.get('endpoint')} not found")

        # check if the endpoint receives arguments
        if len(inspect.signature(endpoint).parameters) > 0:
            args = data.get("args", [])
            if not isinstance(args, list):
                args = [args]
            endpoint: MessageEndpoints = endpoint(*args)
        else:
            endpoint: MessageEndpoints = endpoint()

        await self._update_user_subscriptions(sid, endpoint.endpoint, msg)

    async def _update_user_subscriptions(self, sid: str, endpoint: str, endpoint_request: str):
        deployment = self.users[sid]["deployment"]

        endpoint_info = EndpointInfo(
            RedisAtlasEndpoints.redis_data(deployment, endpoint), Any, MessageOp.STREAM
        )

        room = RedisAtlasEndpoints.socketio_endpoint_room(deployment, endpoint)
        self.redis.register(
            endpoint_info,
            cb=self.on_redis_message,
            parent=self,
            room=room,
            endpoint_request=endpoint_request,
        )
        if endpoint not in self.users[sid]["subscriptions"]:
            await self.socket.enter_room(sid, room)
            self.users[sid]["subscriptions"].append((endpoint, endpoint_request))
            await self.socket.manager.update_websocket_states()

    @staticmethod
    def on_redis_message(message, parent, room, endpoint_request):
        async def emit_message(message):
            if "pubsub_data" in message:
                msg = message["pubsub_data"]
            else:
                msg = message["data"]
            outgoing = {
                "data": msg.content,
                "metadata": msg.metadata,
                "endpoint": room.split("/", 3)[-1],
                "endpoint_request": endpoint_request,
            }
            outgoing = json_ext.dumps(outgoing)
            await parent.socket.emit("message", data=outgoing, room=room)

        # Run the coroutine in this loop
        asyncio.run_coroutine_threadsafe(emit_message(message), parent.loop)
