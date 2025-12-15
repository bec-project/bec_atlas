from unittest import mock

import pytest

from bec_atlas.ingestor.signal.model import SignalGroupInfo
from bec_atlas.ingestor.signal.utils import SignalGroupManager


@pytest.fixture
def group_manager():
    """Create a SignalGroupManager with mocked session."""
    with mock.patch("bec_atlas.ingestor.signal.utils.requests.Session") as mock_session:
        mock_session.return_value = mock.Mock()
        manager = SignalGroupManager(host="http://signal.test", number="+123456789")
        yield manager


def test_get_all_groups_returns_list(group_manager, mock_http_response):
    """Test get_all_groups returns a list of SignalGroupInfo."""
    response = mock_http_response(
        {
            "result": [
                {
                    "name": "Group 1",
                    "id": "group-1",
                    "members": [],
                    "admins": [],
                    "pendingMembers": [],
                    "requestingMembers": [],
                    "banned": [],
                    "groupInviteLink": "https://signal.group/link1",
                    "permissionAddMember": "EVERY_MEMBER",
                    "permissionEditDetails": "ONLY_ADMINS",
                    "permissionSendMessage": "EVERY_MEMBER",
                },
                {
                    "name": "Group 2",
                    "id": "group-2",
                    "members": [],
                    "admins": [],
                    "pendingMembers": [],
                    "requestingMembers": [],
                    "banned": [],
                    "groupInviteLink": "https://signal.group/link2",
                    "permissionAddMember": "EVERY_MEMBER",
                    "permissionEditDetails": "ONLY_ADMINS",
                    "permissionSendMessage": "EVERY_MEMBER",
                },
            ]
        }
    )
    group_manager.session.post.return_value = response

    groups = group_manager.get_all_groups()

    assert len(groups) == 2
    assert all(isinstance(g, SignalGroupInfo) for g in groups)
    assert groups[0].name == "Group 1"
    assert groups[1].name == "Group 2"
    group_manager.session.post.assert_called_once_with(
        "http://signal.test/api/v1/rpc",
        json={"jsonrpc": "2.0", "method": "listGroups", "params": {}, "id": 1},
        timeout=10,
    )


def test_get_all_groups_returns_empty_list(group_manager, mock_http_response):
    """Test get_all_groups returns empty list when no groups exist."""
    response = mock_http_response({"result": None})
    group_manager.session.post.return_value = response

    groups = group_manager.get_all_groups()

    assert groups == []


def test_get_group_by_id_returns_group(group_manager, mock_http_response):
    """Test get_group_by_id returns a SignalGroupInfo when group exists."""
    response = mock_http_response(
        {
            "result": [
                {
                    "name": "Test Group",
                    "id": "group-1",
                    "members": [],
                    "admins": [],
                    "pendingMembers": [],
                    "requestingMembers": [],
                    "banned": [],
                    "groupInviteLink": "https://signal.group/link1",
                    "permissionAddMember": "EVERY_MEMBER",
                    "permissionEditDetails": "ONLY_ADMINS",
                    "permissionSendMessage": "EVERY_MEMBER",
                }
            ]
        }
    )
    group_manager.session.post.return_value = response

    group = group_manager.get_group_by_id("group-1")

    assert isinstance(group, SignalGroupInfo)
    assert group.name == "Test Group"
    assert group.id == "group-1"
    group_manager.session.post.assert_called_once_with(
        "http://signal.test/api/v1/rpc",
        json={"jsonrpc": "2.0", "method": "listGroups", "params": {"groupId": "group-1"}, "id": 1},
        timeout=10,
    )


def test_get_group_by_id_returns_none(group_manager, mock_http_response):
    """Test get_group_by_id returns None when group doesn't exist."""
    response = mock_http_response({"result": []})
    group_manager.session.post.return_value = response

    group = group_manager.get_group_by_id("nonexistent")

    assert group is None


def test_create_new_group_success(group_manager, mock_http_response):
    """Test create_new_group returns group ID on success."""
    response = mock_http_response({"result": {"groupId": "new-group-id"}})
    group_manager.session.post.return_value = response

    group_id = group_manager.create_new_group("New Group", "Test description")

    assert group_id == "new-group-id"
    group_manager.session.post.assert_called_once_with(
        "http://signal.test/api/v1/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "updateGroup",
            "params": {"name": "New Group", "description": "Test description"},
            "id": 1,
        },
        timeout=10,
    )


def test_create_new_group_failure(group_manager, mock_http_response):
    """Test create_new_group returns None on failure."""
    response = mock_http_response({"result": None})
    group_manager.session.post.return_value = response

    group_id = group_manager.create_new_group("New Group")

    assert group_id is None


def test_join_group_success(group_manager, mock_http_response):
    """Test join_group returns group ID on success."""
    response = mock_http_response({"result": {"groupId": "joined-group-id"}})
    group_manager.session.post.return_value = response

    group_id = group_manager.join_group("https://signal.group/invitation")

    assert group_id == "joined-group-id"
    group_manager.session.post.assert_called_once_with(
        "http://signal.test/api/v1/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "joinGroup",
            "params": {"uri": "https://signal.group/invitation"},
            "id": 1,
        },
        timeout=10,
    )


def test_join_group_failure(group_manager, mock_http_response):
    """Test join_group returns None on failure."""
    response = mock_http_response({"result": None})
    group_manager.session.post.return_value = response

    group_id = group_manager.join_group("https://signal.group/invalid")

    assert group_id is None


def test_leave_group_success(group_manager, mock_http_response):
    """Test leave_group returns True on success."""
    # Mock get_group_by_id to return a group with the current user as admin
    mock_get_group = mock_http_response(
        {
            "result": [
                {
                    "name": "Test Group",
                    "id": "group-1",
                    "members": [],
                    "admins": [{"number": "+123456789"}],
                    "pendingMembers": [],
                    "requestingMembers": [],
                    "banned": [],
                    "groupInviteLink": "https://signal.group/link1",
                    "permissionAddMember": "EVERY_MEMBER",
                    "permissionEditDetails": "ONLY_ADMINS",
                    "permissionSendMessage": "EVERY_MEMBER",
                }
            ]
        }
    )

    mock_leave = mock_http_response({"result": {"success": True}})

    group_manager.session.post.side_effect = [mock_get_group, mock_leave]

    result = group_manager.leave_group("group-1")

    assert result is True
    assert group_manager.session.post.call_count == 2


def test_leave_group_with_delete(group_manager, mock_http_response):
    """Test leave_group with delete=True includes delete parameter."""
    mock_get_group = mock_http_response(
        {
            "result": [
                {
                    "name": "Test Group",
                    "id": "group-1",
                    "members": [],
                    "admins": [{"number": "+123456789"}],
                    "pendingMembers": [],
                    "requestingMembers": [],
                    "banned": [],
                    "groupInviteLink": "https://signal.group/link1",
                    "permissionAddMember": "EVERY_MEMBER",
                    "permissionEditDetails": "ONLY_ADMINS",
                    "permissionSendMessage": "EVERY_MEMBER",
                }
            ]
        }
    )

    mock_leave = mock_http_response({"result": {"success": True}})

    group_manager.session.post.side_effect = [mock_get_group, mock_leave]

    result = group_manager.leave_group("group-1", delete=True)

    assert result is True
    call_args = group_manager.session.post.call_args_list[1]
    assert call_args.kwargs["json"]["params"]["delete"] is True


def test_leave_group_fails_when_last_admin(group_manager, mock_http_response):
    """Test leave_group raises error when user is last admin with other members."""
    mock_get_group = mock_http_response(
        {
            "result": [
                {
                    "name": "Test Group",
                    "id": "group-1",
                    "members": [{"number": "+999999999"}, {"number": "+888888888"}],
                    "admins": [{"number": "+123456789"}],
                    "pendingMembers": [],
                    "requestingMembers": [],
                    "banned": [],
                    "groupInviteLink": "https://signal.group/link1",
                    "permissionAddMember": "EVERY_MEMBER",
                    "permissionEditDetails": "ONLY_ADMINS",
                    "permissionSendMessage": "EVERY_MEMBER",
                }
            ]
        }
    )

    group_manager.session.post.return_value = mock_get_group

    with pytest.raises(ValueError, match="Cannot leave group as the last admin"):
        group_manager.leave_group("group-1")


def test_leave_group_returns_false_when_group_not_found(group_manager, mock_http_response):
    """Test leave_group returns False when group doesn't exist."""
    response = mock_http_response({"result": []})
    group_manager.session.post.return_value = response

    result = group_manager.leave_group("nonexistent")

    assert result is False


def test_add_user_to_group_single_user(group_manager, mock_http_response):
    """Test add_user_to_group with a single user."""
    response = mock_http_response({"result": {"success": True}})
    group_manager.session.post.return_value = response

    result = group_manager.add_user_to_group("group-1", "+999999999")

    assert result is True
    group_manager.session.post.assert_called_once_with(
        "http://signal.test/api/v1/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "updateGroup",
            "params": {"groupId": "group-1", "member": "+999999999"},
            "id": 1,
        },
        timeout=10,
    )


def test_add_user_to_group_multiple_users(group_manager, mock_http_response):
    """Test add_user_to_group with multiple users."""
    response = mock_http_response({"result": {"success": True}})
    group_manager.session.post.return_value = response

    result = group_manager.add_user_to_group("group-1", ["+111111111", "+222222222"])

    assert result is True
    call_args = group_manager.session.post.call_args
    assert call_args.kwargs["json"]["params"]["member"] == "+111111111 +222222222"


def test_add_admin_to_group(group_manager, mock_http_response):
    """Test add_admin_to_group."""
    response = mock_http_response({"result": {"success": True}})
    group_manager.session.post.return_value = response

    result = group_manager.add_admin_to_group("group-1", "+999999999")

    assert result is True
    call_args = group_manager.session.post.call_args
    assert call_args.kwargs["json"]["params"]["admin"] == "+999999999"


def test_remove_admin_from_group(group_manager, mock_http_response):
    """Test remove_admin_from_group."""
    response = mock_http_response({"result": {"success": True}})
    group_manager.session.post.return_value = response

    result = group_manager.remove_admin_from_group("group-1", "+999999999")

    assert result is True
    call_args = group_manager.session.post.call_args
    assert call_args.kwargs["json"]["params"]["removeAdmin"] == "+999999999"


def test_remove_user_from_group(group_manager, mock_http_response):
    """Test remove_user_from_group."""
    response = mock_http_response({"result": {"success": True}})
    group_manager.session.post.return_value = response

    result = group_manager.remove_user_from_group("group-1", "+999999999")

    assert result is True
    call_args = group_manager.session.post.call_args
    assert call_args.kwargs["json"]["params"]["removeMember"] == "+999999999"


def test_set_permissions_edit_details_admins_only(group_manager, mock_http_response):
    """Test set_permissions_edit_details with admins_only=True."""
    response = mock_http_response({"result": {"success": True}})
    group_manager.session.post.return_value = response

    result = group_manager.set_permissions_edit_details("group-1", admins_only=True)

    assert result is True
    call_args = group_manager.session.post.call_args
    assert call_args.kwargs["json"]["params"]["setPermissionEditDetails"] == "only-admins"


def test_set_permissions_edit_details_everyone(group_manager, mock_http_response):
    """Test set_permissions_edit_details with admins_only=False."""
    response = mock_http_response({"result": {"success": True}})
    group_manager.session.post.return_value = response

    result = group_manager.set_permissions_edit_details("group-1", admins_only=False)

    assert result is True
    call_args = group_manager.session.post.call_args
    assert call_args.kwargs["json"]["params"]["setPermissionEditDetails"] == "every-member"


def test_set_permissions_add_member(group_manager, mock_http_response):
    """Test set_permissions_add_member."""
    response = mock_http_response({"result": {"success": True}})
    group_manager.session.post.return_value = response

    result = group_manager.set_permissions_add_member("group-1", admins_only=True)

    assert result is True
    call_args = group_manager.session.post.call_args
    assert call_args.kwargs["json"]["params"]["setPermissionAddMember"] == "only-admins"


def test_set_permissions_send_message(group_manager, mock_http_response):
    """Test set_permissions_send_message."""
    response = mock_http_response({"result": {"success": True}})
    group_manager.session.post.return_value = response

    result = group_manager.set_permissions_send_message("group-1", admins_only=False)

    assert result is True
    call_args = group_manager.session.post.call_args
    assert call_args.kwargs["json"]["params"]["setPermissionSendMessages"] == "every-member"


def test_set_expiration_time(group_manager, mock_http_response):
    """Test set_expiration_time."""
    response = mock_http_response({"result": {"success": True}})
    group_manager.session.post.return_value = response

    result = group_manager.set_expiration_time("group-1", 3600)

    assert result is True
    call_args = group_manager.session.post.call_args
    assert call_args.kwargs["json"]["params"]["expiration"] == 3600
