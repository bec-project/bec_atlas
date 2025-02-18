import asyncio
from unittest import mock

import pytest
from bec_lib import messages
from bec_lib.serialization import MsgpackSerialization

from bec_atlas.model.model import BECAccessProfile, DeploymentAccess, User
from bec_atlas.router.redis_router import RemoteAccess


@pytest.fixture
def logged_in_client(backend):
    client, _ = backend
    response = client.post(
        "/api/v1/user/login", json={"username": "admin@bec_atlas.ch", "password": "admin"}
    )
    assert response.status_code == 200
    token = response.json()
    assert isinstance(token, str)
    assert len(token) > 20
    return client


@pytest.fixture
def deployment(logged_in_client):
    client = logged_in_client
    response = client.get("/api/v1/deployments/realm", params={"realm": "demo_beamline_1"})
    assert response.status_code == 200
    return response.json()[0]


@pytest.mark.parametrize(
    "key, patterns, access",
    [
        (
            "public/some/key",
            [
                "%R~public/*",  # Read-only access
                "%R~info/*",  # Read-only access
                "%RW~personal/test_username/*",  # Read/Write access
                "%RW~user/*",  # Read/Write access
            ],
            RemoteAccess.READ,
        ),
        (
            "info/some/key",
            [
                "%R~public/*",  # Read-only access
                "%R~info/*",  # Read-only access
                "%RW~personal/test_username/*",  # Read/Write access
                "%RW~user/*",  # Read/Write access
            ],
            RemoteAccess.READ,
        ),
        (
            "personal/test_username/some/key",
            [
                "%R~public/*",  # Read-only access
                "%R~info/*",  # Read-only access
                "%RW~personal/test_username/*",  # Read/Write access
                "%RW~user/*",  # Read/Write access
            ],
            RemoteAccess.READ_WRITE,
        ),
        (
            "user/some/key",
            [
                "%R~public/*",  # Read-only access
                "%R~info/*",  # Read-only access
                "%RW~personal/test_username/*",  # Read/Write access
                "%RW~user/*",  # Read/Write access
            ],
            RemoteAccess.READ_WRITE,
        ),
        ("user/some/key", ["*"], RemoteAccess.READ_WRITE),
        ("public/some/key", ["%W~public/*"], RemoteAccess.WRITE),
        ("some/key", ["%W~public/*"], RemoteAccess.NONE),
    ],
)
def test_get_key_pattern_access(backend, key, patterns, access):
    _, app = backend
    assert app.redis_router.get_key_pattern_access(key, patterns) == access


@pytest.mark.parametrize(
    "channel, patterns, access",
    [
        (
            "public/some/channel",
            ["public/*", "info/*", "personal/test_username/*", "user/*"],
            RemoteAccess.READ_WRITE,
        ),
        ("some/channel", ["public/*"], RemoteAccess.NONE),
    ],
)
def test_get_channel_pattern_access(backend, channel, patterns, access):
    _, app = backend
    assert app.redis_router.get_channel_pattern_access(channel, patterns) == access


@pytest.mark.parametrize(
    "user, deployment_access, expected_access",
    [
        (
            User(
                owner_groups=["admin"],
                access_groups=["admin"],
                email="admin@bec_atlas.ch",
                groups=["admin"],
                first_name="admin",
                last_name="admin",
            ),
            DeploymentAccess(
                owner_groups=["admin"], access_groups=["admin"], user_read_access=["admin"]
            ),
            RemoteAccess.NONE,
        ),
        (
            User(
                owner_groups=["admin"],
                access_groups=["admin"],
                email="admin@bec_atlas.ch",
                groups=["admin"],
                first_name="admin",
                last_name="admin",
            ),
            DeploymentAccess(
                owner_groups=["admin"], access_groups=["admin"], remote_read_access=["admin"]
            ),
            RemoteAccess.READ,
        ),
        (
            User(
                owner_groups=["admin"],
                access_groups=["admin"],
                email="admin@bec_atlas.ch",
                groups=["admin"],
                first_name="admin",
                last_name="admin",
            ),
            DeploymentAccess(
                owner_groups=["admin"], access_groups=["admin"], remote_write_access=["admin"]
            ),
            RemoteAccess.READ_WRITE,
        ),
    ],
)
def test_get_access(backend, user, deployment_access, expected_access):
    _, app = backend
    assert app.redis_router.get_access(user, deployment_access) == expected_access


@pytest.mark.parametrize(
    "bec_access, key, redis_op, raise_exception",
    [
        # Full access profile - should allow all operations
        (
            BECAccessProfile(
                deployment_id="test_id",
                username="admin",
                owner_groups=["admin"],
                keys=["*"],
                channels=["*"],
                commands=["*"],
            ),
            "some/key",
            "get",
            False,
        ),
        # Read-only access to keys
        (
            BECAccessProfile(
                deployment_id="test_id",
                username="reader",
                owner_groups=["readers"],
                keys=["%R~data/*"],
                channels=["*"],
                commands=["*"],
            ),
            "data/sensor1",
            "get",
            False,
        ),
        # Write operation with read-only access should fail
        (
            BECAccessProfile(
                deployment_id="test_id",
                username="reader",
                owner_groups=["readers"],
                keys=["%R~data/*"],
                channels=["*"],
                commands=["*"],
            ),
            "data/sensor1",
            "set",
            True,
        ),
        # Send operation to allowed channel
        (
            BECAccessProfile(
                deployment_id="test_id",
                username="writer",
                owner_groups=["writers"],
                keys=["*"],
                channels=["commands/*"],
                commands=["*"],
            ),
            "commands/motor1",
            "send",
            False,
        ),
        # Testing set_and_publish with mixed permissions
        (
            BECAccessProfile(
                deployment_id="test_id",
                username="user",
                owner_groups=["users"],
                keys=["%RW~status/*"],
                channels=["status/*"],
                commands=["*"],
            ),
            "status/device1",
            "set_and_publish",
            False,
        ),
        # Testing set_and_publish with insufficient key permissions
        (
            BECAccessProfile(
                deployment_id="test_id",
                username="user",
                owner_groups=["users"],
                keys=["%R~status/*"],
                channels=["status/*"],
                commands=["*"],
            ),
            "status/device1",
            "set_and_publish",
            True,
        ),
        # Testing invalid operation
        (
            BECAccessProfile(
                deployment_id="test_id",
                username="admin",
                owner_groups=["admin"],
                keys=["*"],
                channels=["*"],
                commands=["*"],
            ),
            "some/key",
            "invalid_op",
            True,
        ),
        # Test send operation with insufficient channel permissions
        (
            BECAccessProfile(
                deployment_id="test_id",
                username="user",
                owner_groups=["users"],
                keys=["*"],
                channels=["internal/*"],
                commands=["*"],
            ),
            "status/device1",
            "send",
            True,
        ),
        # Test set_and_publish with insufficient write permissions
        (
            BECAccessProfile(
                deployment_id="test_id",
                username="user",
                owner_groups=["users"],
                keys=["%R~status/*"],
                channels=["status/*"],
                commands=["*"],
            ),
            "status/device1",
            "set_and_publish",
            True,
        ),
        # Test set_and_publish with insufficient channel permissions
        (
            BECAccessProfile(
                deployment_id="test_id",
                username="user",
                owner_groups=["users"],
                keys=["%RW~status*"],
                channels=["internal/*"],
                commands=["*"],
            ),
            "status/device1",
            "set_and_publish",
            True,
        ),
        # Test get operation with insufficient read permissions
        (
            BECAccessProfile(
                deployment_id="test_id",
                username="user",
                owner_groups=["users"],
                keys=["%W~status/*"],
                channels=["status/*"],
                commands=["*"],
            ),
            "status/device1",
            "get",
            True,
        ),
    ],
    ids=[
        "Full access profile - should allow all operations",
        "Read-only access to keys",
        "Write operation with read-only access should fail",
        "Send operation to allowed channel",
        "Testing set_and_publish with mixed permissions",
        "Testing set_and_publish with insufficient key permissions",
        "Testing invalid operation",
        "Test send operation with insufficient channel permissions",
        "Test set_and_publish with insufficient write permissions",
        "Test set_and_publish with insufficient channel permissions",
        "Test get operation with insufficient read permissions",
    ],
)
def test_bec_access_profile_allows_op(backend, bec_access, key, redis_op, raise_exception):
    _, app = backend
    if raise_exception:
        with pytest.raises(Exception):
            app.redis_router.bec_access_profile_allows_op(bec_access, key, redis_op)
    else:
        app.redis_router.bec_access_profile_allows_op(bec_access, key, redis_op)


# @pytest.mark.asyncio
def test_redis_get(logged_in_client, deployment, backend):
    client = logged_in_client
    _, app = backend
    response = client.patch(
        "/api/v1/deployment_access",
        params={"deployment_id": deployment["_id"]},
        json={
            "user_read_access": ["admin@bec_atlas.ch"],
            "remote_read_access": ["admin@bec_atlas.ch"],
        },
    )
    assert response.status_code == 200

    with mock.patch.object(app.redis_router.redis, "pubsub") as pubsub_mock:
        msg = MsgpackSerialization.dumps(
            messages.RawMessage(data={"test_key": "test"}, metadata={"message": "test"})
        )
        response = {
            "type": "message",
            "pattern": None,
            "channel": "internal/deployment",
            "data": msg,
        }

        pubsub_mock().subscribe = mock.AsyncMock()
        ret_msg = pubsub_mock().get_message = mock.AsyncMock()
        ret_msg.side_effect = [None, response]
        response = client.get(
            "/api/v1/redis", params={"deployment": deployment["_id"], "key": "test_key"}
        )
        assert response.status_code == 200
        assert response.json() == {
            "data": {"data": {"test_key": "test"}},
            "metadata": {"message": "test"},
        }
