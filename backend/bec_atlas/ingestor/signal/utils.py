from __future__ import annotations

import requests

from bec_atlas.ingestor.signal.model import SignalGroupInfo


class SignalGroupManager:
    def __init__(self, host: str, number: str):
        self.host = host
        self.number = number
        self.session = requests.Session()

    def get_all_groups(self) -> list[SignalGroupInfo]:
        """
        Get all groups from the signal server.

        Args:
            host (str): The signal server host.
        Returns:
            list[SignalGroupInfo]: List of groups.
        """
        result = self._run("listGroups", {}) or []
        return [SignalGroupInfo(**group) for group in result]

    def get_group_by_id(self, group_id: str) -> SignalGroupInfo | None:
        """
        Get a group by its ID.

        Args:
            group_id (str): The group ID.
        Returns:
            SignalGroupInfo | None: The group info or None if not found.
        """
        result = self._run("listGroups", {"groupId": group_id}) or []
        if result:
            return SignalGroupInfo(**result[0])
        return None

    def create_new_group(self, name: str, description: str = "") -> str | None:
        """
        Create a new group.

        Args:
            name (str): The group name.
            description (str): The group description.
        Returns:
            str | None: The created group ID or None if creation failed.
        """
        result = self._run("updateGroup", {"name": name, "description": description})
        if result:
            return result.get("groupId")
        return None

    def join_group(self, invitation_link: str) -> str | None:
        """
        Join a group using an invitation link.

        Args:
            invitation_link (str): The invitation link.
        Returns:
            str | None: The group ID if the operation was successful, None otherwise.
        """
        params = {"uri": invitation_link}
        result = self._run("joinGroup", params)
        if result:
            return result.get("groupId")
        return None

    def leave_group(self, group_id: str, delete: bool = False) -> bool:
        """
        Leave a group. If delete is True, the group will be deleted.

        Args:
            group_id (str): The group ID.
            delete (bool): Whether to delete the group.
        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        # If we are the last admin but there are other members, we cannot leave the group.
        group_info = self.get_group_by_id(group_id)
        if group_info is None:
            return False
        if len(group_info.admins) == 1 and len(group_info.members) > 1:
            if group_info.admins[0].number == self.number:
                raise ValueError("Cannot leave group as the last admin while other members exist.")
        params: dict = {"groupId": group_id}
        if delete:
            params["delete"] = True
        result = self._run("quitGroup", params)
        return result is not None

    def add_user_to_group(self, group_id: str, user_id: str | list[str]) -> bool:
        """
        Add a user to a group.

        Args:
            group_id (str): The group ID.
            user_id (str | list[str]): The user ID or list of user IDs.
        Returns:
            bool: True if the user was added successfully, False otherwise.
        """
        user_ids = " ".join(user_id) if isinstance(user_id, list) else user_id
        result = self._run("updateGroup", {"groupId": group_id, "member": user_ids})
        return result is not None

    def add_admin_to_group(self, group_id: str, user_id: str | list[str]) -> bool:
        """
        Add an admin to a group.

        Args:
            group_id (str): The group ID.
            user_id (str | list[str]): The user ID or list of user IDs.
        Returns:
            bool: True if the admin was added successfully, False otherwise.
        """
        user_ids = " ".join(user_id) if isinstance(user_id, list) else user_id
        result = self._run("updateGroup", {"groupId": group_id, "admin": user_ids})
        return result is not None

    def remove_admin_from_group(self, group_id: str, user_id: str | list[str]) -> bool:
        """
        Remove an admin from a group.

        Args:
            group_id (str): The group ID.
            user_id (str | list[str]): The user ID or list of user IDs.
        Returns:
            bool: True if the admin was removed successfully, False otherwise.
        """
        user_ids = " ".join(user_id) if isinstance(user_id, list) else user_id
        result = self._run("updateGroup", {"groupId": group_id, "removeAdmin": user_ids})
        return result is not None

    def remove_user_from_group(self, group_id: str, user_id: str | list[str]) -> bool:
        """
        Remove a user from a group.

        Args:
            group_id (str): The group ID.
            user_id (str | list[str]): The user ID or list of user IDs.
        Returns:
            bool: True if the user was removed successfully, False otherwise.
        """
        user_ids = " ".join(user_id) if isinstance(user_id, list) else user_id
        result = self._run("updateGroup", {"groupId": group_id, "removeMember": user_ids})
        return result is not None

    def set_permissions_edit_details(self, group_id: str, admins_only: bool) -> bool:
        """
        Set whether members can edit group details.

        Args:
            group_id (str): The group ID.
            admins_only (bool): Whether only admins can edit details.
        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        flag = "every-member" if not admins_only else "only-admins"
        result = self._run("updateGroup", {"groupId": group_id, "setPermissionEditDetails": flag})
        return result is not None

    def set_permissions_add_member(self, group_id: str, admins_only: bool) -> bool:
        """
        Set whether members can add new members to the group.

        Args:
            group_id (str): The group ID.
            admins_only (bool): Whether only admins can add new members.
        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        flag = "every-member" if not admins_only else "only-admins"
        result = self._run("updateGroup", {"groupId": group_id, "setPermissionAddMember": flag})
        return result is not None

    def set_permissions_send_message(self, group_id: str, admins_only: bool) -> bool:
        """
        Set whether members can send messages to the group.

        Args:
            group_id (str): The group ID.
            admins_only (bool): Whether only admins can send messages.
        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        flag = "every-member" if not admins_only else "only-admins"
        result = self._run("updateGroup", {"groupId": group_id, "setPermissionSendMessages": flag})
        return result is not None

    def set_expiration_time(self, group_id: str, expiration_time_seconds: int) -> bool:
        """
        Set the expiration time for messages in the group.

        Args:
            group_id (str): The group ID.
            expiration_time_seconds (int): The expiration time in seconds. Set to 0 for no expiration.
        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        result = self._run(
            "updateGroup", {"groupId": group_id, "expiration": expiration_time_seconds}
        )
        return result is not None

    def _run(self, method: str, params: dict) -> dict | None:
        """
        Run a JSON-RPC method on the signal server.
        Args:
            method (str): The method name.
            params (dict): The method parameters.
        Returns:
            dict | None: The result of the method call or None if not found.
        """
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        response = self.session.post(f"{self.host}/api/v1/rpc", json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get("result")


if __name__ == "__main__":  # pragma: no cover
    from bec_atlas.utils.env_loader import load_env

    config = load_env()
    host = config.get("signal", {}).get("host")
    number = config.get("signal", {}).get("number")
    manager = SignalGroupManager(host=host, number=number)

    groups = manager.get_all_groups()
    print(groups)

    # groups = manager.get_all_groups()
    # # print(groups)
    # group = manager.get_group_by_id(group_id="group_id_here")

    # manager.leave_group(group_id="group_id_here", delete=True)
