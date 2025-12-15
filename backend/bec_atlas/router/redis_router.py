from __future__ import annotations

import asyncio
import enum
import functools
import inspect
import json
import traceback
import uuid
from typing import TYPE_CHECKING, Any, Literal

import socketio
from bec_lib import messages
from bec_lib.endpoints import EndpointInfo, MessageEndpoints, MessageOp
from bec_lib.logger import bec_logger
from bec_lib.serialization import MsgpackSerialization, json_ext
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from bec_atlas.authentication import convert_to_user, get_current_user, get_current_user_sync
from bec_atlas.datasources.endpoints import RedisAtlasEndpoints
from bec_atlas.model.model import BECAccessProfile, DeploymentAccess, User
from bec_atlas.router.base_router import BaseRouter

logger = bec_logger.logger

if TYPE_CHECKING:  # pragma: no cover
    from bec_lib.redis_connector import RedisConnector

    from bec_atlas.datasources.datasource_manager import DatasourceManager
    from bec_atlas.main import AtlasApp


class RemoteAccess(enum.Enum):
    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"
    NONE = "none"


class MsgResponse(Response):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return content.encode()


class RedisRouter(BaseRouter):
    """
    This class is a router for the Redis API. It exposes the redis client through
    the API. For pub/sub and stream operations, a websocket connection can be used.
    """

    def __init__(self, prefix="/api/v1", datasources: DatasourceManager = None):
        super().__init__(prefix, datasources)
        self.redis = self.datasources.redis.async_connector
        self.db = self.datasources.mongodb

        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route(
            "/redis", self.redis_get, methods=["GET"], response_class=MsgResponse
        )
        self.router.add_api_route("/redis", self.redis_post, methods=["POST"])
        self.router.add_api_route("/redis", self.redis_delete, methods=["DELETE"])

    @convert_to_user
    async def redis_get(
        self, deployment: str, key: str = Query(...), current_user: User = Depends(get_current_user)
    ) -> str:
        """
        Get a message from the BEC instance of the specified deployment.
        Args:
            deployment (str): The deployment id
            key (str): The key in Redis
            current_user (User): The current user
        Returns:
            str: The response message
        """
        self.validate_user_bec_access(current_user, deployment, key, "get", "read")
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
        if response is None:
            return json_ext.dumps({"error": "Timeout waiting for response"})
        out = MsgpackSerialization.loads(response["data"])
        return json_ext.dumps({"data": out.content, "metadata": out.metadata})

    @convert_to_user
    async def redis_post(
        self,
        deployment: str,
        key: str,
        value: dict,
        redis_op: Literal["send", "set_and_publish", "lpush", "rpush", "set", "xadd"],
        msg_type: str,
        current_user: User = Depends(get_current_user),
    ) -> dict:
        """
        Send a message to the BEC instance of the specified deployment.

        Args:
            deployment (str): The deployment id
            key (str): The key in Redis
            value (dict): The value to send
            redis_op (str): The operation to perform
            msg_type (str): The message type
            current_user (User): The current user

        Raises:
            HTTPException: If the user does not have access to the key or if the message type is invalid

        Returns:
            dict: The response message
        """
        self.validate_user_bec_access(current_user, deployment, key, redis_op, "write")
        msg_obj = getattr(messages, msg_type, None)
        if not isinstance(msg_obj, type) or not issubclass(msg_obj, messages.BECMessage):
            raise HTTPException(status_code=400, detail="Invalid message type.")
        try:
            msg = msg_obj(**value)
        except TypeError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        # msg_dump = MsgpackSerialization.dumps(msg)
        data = MsgpackSerialization.dumps(
            messages.RawMessage(data={"action": redis_op, "key": key, "value": msg})
        )
        request_endpoint = RedisAtlasEndpoints.redis_request(deployment)
        pubsub = self.redis.pubsub()
        pubsub.ignore_subscribe_messages = True
        await self.redis.publish(request_endpoint, data)
        return {"status": "success"}

    @convert_to_user
    async def redis_delete(
        self, deployment: str, key: str, current_user: User = Depends(get_current_user)
    ):
        request_endpoint = RedisAtlasEndpoints.redis_request(deployment)
        pubsub = self.redis.pubsub()
        pubsub.ignore_subscribe_messages = True
        data = {"action": "delete", "key": key}
        await self.redis.publish(request_endpoint, data)

    def validate_user_bec_access(
        self,
        user: User,
        deployment: str,
        key: str,
        redis_op: str,
        operation_type: Literal["read", "write"],
    ):
        """
        Validate the user access to the specified key and operation for the specified deployment.

        Args:
            user (User): The user object
            deployment (str): The deployment name
            key (str): The key in Redis
            operation_type (str): The operation type (read or write)

        Raises:
            HTTPException: If the user does not have access to the key
            ValueError: If the operation is invalid
        """
        deployment_access = self.db.find_one(
            "deployment_access", {"_id": ObjectId(deployment)}, DeploymentAccess
        )
        if not deployment_access:
            raise ValueError("Deployment not found")
        access = self.get_access(user, deployment_access)

        # check if the user has access to the deployment
        if access == RemoteAccess.NONE:
            raise HTTPException(
                status_code=403, detail="User does not have remote access to the deployment"
            )
        if operation_type == "read":
            if access not in [RemoteAccess.READ, RemoteAccess.READ_WRITE]:
                raise HTTPException(status_code=403, detail="User does not have read access")
        elif operation_type == "write":
            if access != RemoteAccess.READ_WRITE:
                raise HTTPException(status_code=403, detail="User does not have write access")
        else:
            raise ValueError("Invalid operation type")

        # check if the user has access to the key
        bec_access = self.db.find_one(
            "bec_access_profiles",
            {"deployment_id": deployment, "username": {"$in": [user.email, user.username]}},
            BECAccessProfile,
            user=user,
        )
        if not bec_access:
            raise HTTPException(status_code=403, detail="User does not have access to the key")

        self.bec_access_profile_allows_op(bec_access, key, redis_op)

    def bec_access_profile_allows_op(self, bec_access: BECAccessProfile, key: str, redis_op: str):
        """
        Check if the BEC access profile allows the operation on the key.

        Args:
            bec_access (BECAccessProfile): The BEC access profile
            key (str): The key in Redis
            redis_op (str): The operation to perform

        Raises:
            HTTPException: If the user does not have access to the key
            ValueError: If the operation is invalid
        """
        if redis_op in ["lpush", "rpush", "set", "xadd", "delete"]:
            access = self.get_key_pattern_access(key, bec_access.keys)
            if access not in [RemoteAccess.WRITE, RemoteAccess.READ_WRITE]:
                raise HTTPException(status_code=403, detail="User does not have access to the key")
        elif redis_op == "send":
            access = self.get_channel_pattern_access(key, bec_access.channels)
            if access not in [RemoteAccess.WRITE, RemoteAccess.READ_WRITE]:
                raise HTTPException(status_code=403, detail="User does not have access to the key")
        elif redis_op == "set_and_publish":
            access = self.get_key_pattern_access(key, bec_access.keys)
            if access not in [RemoteAccess.WRITE, RemoteAccess.READ_WRITE]:
                raise HTTPException(status_code=403, detail="User does not have access to the key")
            access = self.get_channel_pattern_access(key, bec_access.channels)
            if access not in [RemoteAccess.WRITE, RemoteAccess.READ_WRITE]:
                raise HTTPException(status_code=403, detail="User does not have access to the key")
        elif redis_op == "get":
            access = self.get_key_pattern_access(key, bec_access.keys)
            if access not in [RemoteAccess.READ, RemoteAccess.READ_WRITE]:
                raise HTTPException(status_code=403, detail="User does not have access to the key")
        else:
            raise ValueError("Invalid operation")

    @staticmethod
    def get_key_pattern_access(key: str, patterns: list[str]) -> RemoteAccess:
        """
        Check if the key matches the pattern.

        Args:
            key (str): The key
            patterns (list[str]): The patterns

        Returns:
            RemoteAccess: The access level if the key matches the pattern, RemoteAccess.NONE otherwise
        """
        if "*" in patterns:
            return RemoteAccess.READ_WRITE
        for pattern in patterns:
            components = pattern.split("~")
            rule = components[0]
            subpattern = "".join(components[1:]).split("*", maxsplit=1)[0]
            if subpattern in key:
                if rule == "%R":
                    return RemoteAccess.READ
                if rule == "%W":
                    return RemoteAccess.WRITE
                if rule == "%RW":
                    return RemoteAccess.READ_WRITE
        return RemoteAccess.NONE

    @staticmethod
    def get_channel_pattern_access(channel: str, patterns: list[str]) -> RemoteAccess:
        """
        Check if the channel matches the pattern.

        Args:
            channel (str): The channel
            patterns (list[str]): The patterns

        Returns:
            RemoteAccess: The access level if the channel matches the pattern, RemoteAccess.NONE otherwise
        """
        for pattern in patterns:
            prefix = pattern.split("*")[0]
            if prefix in channel:
                return RemoteAccess.READ_WRITE
        return RemoteAccess.NONE

    @staticmethod
    def get_access(user: User, deployment_access: DeploymentAccess) -> RemoteAccess:
        """
        Get the access level of the user to the deployment.
        """
        access = RemoteAccess.NONE
        groups = set(user.groups)
        if user.username is not None:
            groups.add(user.username)
        if user.email is not None:
            groups.add(user.email)

        if groups & set(deployment_access.remote_read_access):
            access = RemoteAccess.READ
        if groups & set(deployment_access.remote_write_access):
            access = RemoteAccess.READ_WRITE
        return access


def safe_socket(fcn):
    """
    Decorator to safely handle socket functions by catching exceptions and emitting error messages.
    """

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

    def start_update_loop(self) -> asyncio.Task:
        """
        Start the update loop for the websocket state information.
        This loop will periodically update the state information for all deployments.

        Returns:
            asyncio.Task: The task for the update loop
        """
        self.started_update_loop = True
        loop = asyncio.get_event_loop()
        task = loop.create_task(self._backend_heartbeat())
        return task

    async def disconnect(
        self, sid: str, namespace: str, ignore_queue: bool = False, **kwargs
    ) -> None:
        """
        Disconnect a client from the websocket.

        Args:
            sid (str): The socket id of the client
            namespace (str): The namespace of the client
            ignore_queue (bool): Whether to ignore the message queue and disconnect directly
        """
        if ignore_queue:
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

    async def enter_room(
        self, sid: str, namespace: str, room: str, eio_sid: str | None = None
    ) -> None:
        """
        Enter a client into a room.

        Args:
            sid (str): The socket id of the client
            namespace (str): The namespace of the client
            room (str): The room to enter
            eio_sid (str | None, optional): The Engine.IO session id. Defaults to None.
        """
        await super().enter_room(sid, namespace, room, eio_sid=eio_sid)
        await self.update_state_info()

    async def leave_room(self, sid: str, namespace: str, room: str) -> None:
        """
        Leave a client from a room.

        Args:
            sid (str): The socket id of the client
            namespace (str): The namespace of the client
            room (str): The room to leave
        """
        await super().leave_room(sid, namespace, room)
        await self.update_state_info()

    async def _backend_heartbeat(self) -> None:
        """
        Backend heartbeat loop to periodically update the state information for all deployments.
        """
        while not self.parent.fastapi_app.server.should_exit:
            await asyncio.sleep(10)
            await self.update_state_info()

    async def update_state_info(self):
        """
        Update the state information for all deployments.
        This includes the users and their subscriptions per deployment.
        """
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


class AtlasSocketioServer(socketio.AsyncServer):
    manager: BECAsyncRedisManager


class RedisWebsocket:
    """
    This class is a websocket handler for the Redis API. It exposes the redis client through
    the websocket.
    """

    def __init__(self, prefix="/api/v1", datasources=None, app: AtlasApp = None):
        if not datasources:
            raise ValueError("Datasources must be provided")
        self.redis: RedisConnector = datasources.redis.connector
        self.prefix = prefix
        self.fastapi_app = app
        self.redis_router = app.redis_router
        self.active_connections = set()
        redis_host = datasources.redis.config["host"]
        redis_port = datasources.redis.config["port"]
        redis_username = datasources.redis.config.get("username", "ingestor")
        redis_password = datasources.redis.config.get("password")
        self.db = datasources.mongodb
        self.socket = AtlasSocketioServer(
            transports=["websocket"],
            ping_timeout=60,
            cors_allowed_origins="*",
            async_mode="asgi",
            client_manager=BECAsyncRedisManager(
                self,
                url=f"redis://{redis_host}:{redis_port}/0",
                redis_options={"username": redis_username, "password": redis_password},
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

    def _validate_new_user(self, http_query: str | None, auth_token: str) -> tuple:
        """
        Validate the connection of a new user. In particular,
        the user must provide a valid token as well as have access
        to the deployment. If subscriptions are provided, the user
        must have access to the endpoints.

        Args:
            http_query (str): The query parameters of the websocket connection
            auth_token (str): The authentication token of the user

        Returns:
            tuple: The user object, deployment id, and access level

        """
        if not http_query:
            raise ValueError("Query parameters not found")
        if isinstance(http_query, str):
            query = json.loads(http_query)
        else:
            query = http_query

        user_info = get_current_user_sync(auth_token)
        user = self.db.find_one("users", {"email": user_info.email}, User)

        deployment = query.get("deployment")
        if not deployment:
            raise ValueError("Deployment not found in query parameters")

        deployment_access = self.db.find_one(
            "deployment_access", {"_id": ObjectId(deployment)}, DeploymentAccess
        )
        if not deployment_access:
            raise ValueError("Deployment not found")

        access = self.redis_router.get_access(user, deployment_access)
        if access == RemoteAccess.NONE:
            raise ValueError("User does not have remote access to the deployment")

        return user, deployment, access

    @safe_socket
    async def connect_client(self, sid, environ: dict | None = None, auth=None, **kwargs):
        """
        Connect a new client to the websocket.

        Args:
            sid (str): The socket id of the client
            environ (dict): The environment of the websocket connection
            auth (str): The authentication token of the user
        """
        if sid in self.users:
            logger.info("User already connected")
            return

        environ = environ or {}

        http_query = environ.get("HTTP_QUERY") or auth

        cookies = environ.get("HTTP_COOKIE", "")
        auth_token = None

        for cookie in cookies.split("; "):
            if cookie.startswith("access_token="):
                auth_token = cookie.split("=")[1]
                break

        if not auth_token:
            await self.disconnect_client(sid)  # Reject connection
            return

        try:
            user, deployment, access = self._validate_new_user(http_query, auth_token)
        except ValueError:
            await self.disconnect_client(sid, reason="Invalid user or deployment")
            return

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

        if user.email in info:
            self.users[sid] = {"user": user.email, "subscriptions": [], "deployment": deployment}
            for endpoint, endpoint_request in info[user]:
                print(f"Registering {endpoint}")
                await self._update_user_subscriptions(sid, endpoint, endpoint_request)
        else:
            self.users[sid] = {"user": user.email, "subscriptions": [], "deployment": deployment}

        await self.socket.manager.update_websocket_states()

    async def disconnect_client(self, sid, reason: str = None, _environ=None):
        """
        Disconnect a client from the websocket.

        Args:
            sid (str): The socket id of the client
            reason (str): The reason for disconnection
            _environ (dict): The environment of the websocket connection
        """
        is_exit = self.fastapi_app.server.should_exit
        if is_exit:
            return
        if reason:
            await self.socket.emit("error", {"error": reason}, room=sid)
        if sid in self.users:
            del self.users[sid]
        await self.socket.disconnect(sid)

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
