from __future__ import annotations

import base64
import json
import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Literal, cast

import numpy as np
import requests
from bec_lib import messages
from bec_lib.endpoints import MessageEndpoints
from bson import ObjectId

from bec_atlas.datasources.endpoints import RedisAtlasEndpoints
from bec_atlas.ingestor.signal.model import SignalEventMessage
from bec_atlas.ingestor.signal.utils import SignalGroupManager

if TYPE_CHECKING:
    from bec_lib.redis_connector import MessageObject

    from bec_atlas.ingestor.ingestor_base import IngestorBase
    from bec_atlas.model import Deployments


def load_messages() -> dict[Literal["enter", "exit"], list[str]]:
    current_dir = Path(__file__).parent
    with open(current_dir / "signal" / "messages.json", "r") as f:
        return json.load(f)


class EventSubscriber:
    def __init__(self, host: str, on_event: Callable[[dict], None]):
        self._message_prefix = "data:"
        self.host = host
        self.on_event = on_event
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        """
        Start the event subscriber.
        """
        self._thread.start()

    def stop(self):
        """
        Stop the event subscriber.
        """
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                with requests.get(
                    f"{self.host}/api/v1/events",
                    stream=True,
                    timeout=None,
                    headers={"Accept": "text/event-stream"},
                ) as r:
                    r.raise_for_status()
                    r.encoding = "utf-8"

                    for line in r.iter_lines(decode_unicode=True):
                        if self._stop.is_set():
                            return

                        if line and line.startswith(self._message_prefix):
                            msg = json.loads(line.removeprefix(self._message_prefix).strip())
                            self.on_event(msg)

            except Exception as exc:
                # network error, server restart, etc.
                time.sleep(2)
                print("SSE disconnected, retrying:", exc)


class SignalManager:
    """
    Manages the data exchange for Signal messages.
    """

    def __init__(self, ingestor: IngestorBase, config: dict):
        self.ingestor = ingestor
        self.config = config
        self.host = config.get("host", "").rstrip("/")
        self.number = config.get("number")
        if not self.host or not self.number:
            raise ValueError("SignalManager requires 'host' and 'number' in config.")
        self.session = requests.Session()
        self.group_manager = SignalGroupManager(host=self.host, number=self.number)
        self.subscriber = EventSubscriber(host=self.host, on_event=self._handle_event)
        self.subscriber.start()
        self.pending_signal_requests: dict[str, dict] = {}
        self.auto_messages = load_messages()
        self.ingestor.redis.register(
            RedisAtlasEndpoints.signal_link_requests(),
            cb=self._handle_signal_link_request,
            parent=self,
        )
        self.ingestor.redis.register(
            RedisAtlasEndpoints.signal_group_updates(),
            cb=self._handle_signal_message_update,
            parent=self,
        )
        self.shutdown_event = threading.Event()
        self.cleanup_thread: threading.Thread | None = None
        self.start_cleanup()

    def process(
        self, msg: messages.MessagingServiceMessage, deployment: messages.DeploymentInfoMessage
    ):
        """
        Process a Signal message.

        Args:
            msg (messages.MessagingServiceMessage): The message.
            deployment (messages.DeploymentInfoMessage): The deployment info message.

        """
        if not msg.scope:
            print(
                f"No scope found in message for deployment {deployment.deployment_id}, cannot process message."
            )
            return
        if not isinstance(msg.scope, list):
            msg.scope = [msg.scope]

        for scope in msg.scope:
            group_id = self.get_group_id_for_deployment(deployment, scope)
            if not group_id:
                print(
                    f"No Signal group found for deployment {deployment.deployment_id} and scope {scope}, cannot process message."
                )
                return
            payload = {
                "jsonrpc": "2.0",
                "method": "send",
                "params": {"message": self.get_text_from_message(msg), "groupId": group_id},
            }
            self.add_attachments_to_payload(msg, payload)
            self.add_stickers_to_payload(msg, payload)
            self.post(payload)

    def add_attachments_to_payload(self, msg: messages.MessagingServiceMessage, payload: dict):
        """
        Add attachments from the message to the payload to be sent to the Signal server.

        Args:
            msg (messages.MessagingServiceMessage): The message containing the attachments.
            payload (dict): The payload to which the attachments should be added.

        """
        attachments = []
        for msg_part in msg.message:
            if isinstance(msg_part, messages.MessagingServiceFileContent):
                attachments.append(
                    f"data:{msg_part.mime_type};filename={msg_part.filename};base64,{base64.b64encode(msg_part.data).decode()}"
                )
        if attachments:
            payload["params"]["attachments"] = attachments

    def add_stickers_to_payload(self, msg: messages.MessagingServiceMessage, payload: dict):
        """
        Add stickers from the message to the payload to be sent to the Signal server.

        Args:
            msg (messages.MessagingServiceMessage): The message containing the stickers.
            payload (dict): The payload to which the stickers should be added.

        """
        for msg_part in msg.message:
            if isinstance(msg_part, messages.MessagingServiceStickerContent):
                payload["params"]["sticker"] = msg_part.sticker_id

    def get_group_id_for_deployment(
        self, deployment: messages.DeploymentInfoMessage, scope: str
    ) -> str | None:
        """
        Get the Signal group id for a given deployment and scope.

        Args:
            deployment (messages.DeploymentInfoMessage): The deployment info message.
            scope (str): The message scope.

        Returns:
            str | None: The group id if found, None otherwise.
        """

        def _check_services(services):
            for service in services:
                if service.service_type != "signal":
                    continue
                service = cast(messages.SignalServiceInfo, service)
                if service.scope == scope and service.group_id:
                    return service.group_id
            return None

        if deployment.active_session:
            group_id = _check_services(deployment.active_session.messaging_services)
            if group_id:
                return group_id

        group_id = _check_services(deployment.messaging_services)
        if group_id:
            return group_id

        return None

    def get_text_from_message(self, msg: messages.MessagingServiceMessage) -> str:
        """
        Extract the text from a MessagingServiceMessage.

        Args:
            msg (messages.MessagingServiceMessage): The message.
        Returns:
            str: The text content of the message.
        """
        out = ""
        for msg_part in msg.message:
            if isinstance(msg_part, messages.MessagingServiceTextContent):
                out += msg_part.content + "\n"
        return out.strip()

    def post(self, payload: dict):
        """
        Post a payload to the Signal server.
        Args:
            payload (dict): The payload to post.

        """
        self.session.post(f"{self.host}/api/v1/rpc", json=payload, timeout=10)

    def _handle_event(self, event: dict):
        try:
            signal_event = SignalEventMessage(**event)
            print("Received Signal event:", signal_event.model_dump(exclude_defaults=True))
            if signal_event.envelope.dataMessage:
                if self.check_pending_signal_link_request(signal_event):
                    return
                if self.check_direct_mention(signal_event):
                    return
        except Exception as e:
            print("Failed to parse event:", e)
            print("Event data:", event)
            return

    def check_direct_mention(self, signal_event: SignalEventMessage) -> bool:
        """
        Check if the incoming Signal event is a direct mention to BEC, i.e. by mentioning BEC in a group.

        Args:
            signal_event (SignalEventMessage): The incoming Signal event to check for direct mentions.

        Returns:
            bool: True if the event is a direct mention to BEC and processed, False otherwise.

        """
        data_message = signal_event.envelope.dataMessage
        if not data_message:
            return False
        group_info = data_message.groupInfo
        if not group_info:
            return False
        mentions = data_message.mentions
        if not mentions:
            return False
        for mention in mentions:
            if mention.number == self.number:
                # We have been mentioned in a group, we can process this as a direct mention.
                message = data_message.message
                if not message:
                    return False
                message = message.strip()
                self.handle_direct_message(signal_event)
                return True
        return False

    def check_pending_signal_link_request(self, signal_event: SignalEventMessage) -> bool:
        """
        Check if the incoming Signal event was triggered by a phone number for which we currently have a pending signal link request.
        If so, we check if the message contains a group link, and if it does, we complete the linking process for the corresponding session.

        Args:
            signal_event (SignalEventMessage): The incoming Signal event to check against pending link requests.

        Returns:
            bool: True if the event was associated with a pending signal link request and processed, False otherwise.

        """
        source_number = signal_event.envelope.sourceNumber
        if not source_number:
            return False

        data_message = signal_event.envelope.dataMessage
        if not data_message:
            return False
        group_info = data_message.groupInfo
        if group_info:
            # This is a message from a group, we ignore it for the linking process, as we only want to process messages from individuals that are trying to link a session.
            return False
        message = data_message.message
        if not message:
            return False
        message = message.strip()
        if not message.startswith("https://signal.group/"):
            print(
                f"Received message from {source_number} that is not a group link, ignoring for signal linking process."
            )
            return False
        pending_request = self.pending_signal_requests.get(source_number)
        if not pending_request:
            message = "Your signal group link has been received, but no pending signal link request was found. Please initiate the linking process first."
            self.send_message_to_individuals(source_number, message)
            return False
        # We have a pending signal link request for this number, and the message contains a group link, so we proceed with the linking process.
        link = message.split()[0]
        self.complete_signal_linking(source_number, link)
        return True

    def complete_signal_linking(self, number: str, link: str):
        """
        Complete the signal linking process for a pending signal link request.

        Args:
            number (str): The phone number for which to complete the linking process.
            link (str): The group link to associate with the session.

        """
        pending_request = self.pending_signal_requests.pop(number, None)
        if not pending_request:
            print(
                f"No pending signal link request found for number {number} when trying to complete linking."
            )
            return
        group_id = self.group_manager.join_group(link)
        if group_id:
            self.send_random_message(group_id, "enter")
        else:
            groups = self.group_manager.get_all_groups()
            for group in groups:
                if group.groupInviteLink != link:
                    continue
                # we already are a member of the group, so we can just use the group id
                group_id = group.id
                for banned_user in group.banned:
                    if banned_user.number == self.number:
                        message = "Your link request has been received, but BEC is currently banned from the group. Please add BEC back to the group."
                        self.send_message_to_individuals(number, message)
                        return
                break
        if not group_id:
            message = "Your link request has been received, but no matching group was found on the Signal server. Please make sure to send a valid group link."
            self.send_message_to_individuals(number, message)
            return

        patch_data = {"group_id": group_id, "group_link": link}
        service_id = pending_request.get("messaging_service_id")
        if service_id:
            # patch the message service info in MongoDB
            self.ingestor.datasource.patch(
                "messaging_services", ObjectId(service_id), patch_data, dtype=None
            )

            # Send out an updated deployment info message
            if pending_request.get("session"):
                deployment_id = pending_request["session"]["deployment_id"]
            else:
                deployment_id = pending_request["deployment_id"]
            self.ingestor.broadcast_deployment_update(deployment_id)

        self.send_message_to_individuals(number, "Your Signal group has been successfully linked.")

    def send_random_message(self, group_id: str, message_type: Literal["enter", "exit"]):
        """
        Send a random message to a Signal group.

        Args:
            group_id (str): The group ID to send the message to.
            message_type (Literal["enter", "exit"]): The type of message to send.

        """
        messages = self.auto_messages.get(message_type, [])
        if not messages:
            print(f"No {message_type} messages found in configuration.")
            return

        message = str(np.random.choice(messages))
        payload = {
            "jsonrpc": "2.0",
            "method": "send",
            "params": {"message": message, "groupId": group_id},
        }
        self.post(payload)

    @staticmethod
    def _handle_signal_link_request(msg_obj: MessageObject, parent: SignalManager):
        """
        Handle incoming signal link requests from the session router.

        Args:
            msg_obj (MessageObject): The message object containing the session_id and number.
            parent (SignalManager): The parent SignalManager instance.
        """
        msg: messages.VariableMessage = msg_obj.value

        data = msg.value
        number = data.get("number")
        if not number:
            print("Invalid signal link request message:", msg)
            return

        # Store the pending signal link request, so that when we receive the corresponding event from the Signal server,
        # we can correlate it with the session and complete the linking process.
        parent.pending_signal_requests[number] = data
        parent.send_signal_link_request(number)

    def send_signal_link_request(self, number: str):
        """
        Send a signal link request to the Signal server.

        Args:
            number (str): The phone number for which the link request is being made.

        """
        pending_request = self.pending_signal_requests.get(number)
        if not pending_request:
            print(
                f"No pending signal link request found for number {number} when trying to send link request."
            )
            return
        if pending_request.get("session_id"):
            link_scope = f"sessions {pending_request['session']['name']}"
        else:
            link_scope = f"{pending_request['deployment']['realm_id']} deployment {pending_request['deployment']['name']}"
        if not pending_request:
            print(f"No pending signal link request found for number {number}")
            return
        message = (
            f"A request has been made to link the {link_scope} with a new group in Signal.\n\n"
            f"If you want to proceed with the linking, please reply to this message with a group link within the next 5 minutes."
        )
        self.send_message_to_individuals(number, message)

    def send_message_to_individuals(self, number: str | list[str], message: str):
        """
        Send a message to an individual phone number or a list of phone numbers.

        Args:
            number (str | list[str]): The phone number(s) to send the message to.
            message (str): The message content to send.

        """
        if isinstance(number, str):
            recipients = [number]
        else:
            recipients = number
        payload = {
            "jsonrpc": "2.0",
            "method": "send",
            "params": {"message": message, "recipients": recipients},
        }
        self.post(payload)

    def handle_direct_message(self, signal_event: SignalEventMessage):
        """
        Handle a direct mention message from a Signal group.

        For now this is just a placeholder that can be expanded in the future to implement functionality for direct mentions, e.g. by parsing commands from the message content.

        Args:
            signal_event (SignalEventMessage): The incoming Signal event containing the direct mention.

        """

    @staticmethod
    def _handle_signal_message_update(msg_obj: MessageObject, parent: SignalManager):
        """
        Handle incoming signal message updates from the session router.

        Args:
            msg_obj (MessageObject): The message object containing the session_id, deployment_id, and the updated message.
            parent (SignalManager): The parent SignalManager instance.
        """
        msg: messages.VariableMessage = msg_obj.value
        data = msg.value
        action = data.get("action")

        match action:
            case "join":
                group_link = data.get("group_link")
                if group_link:
                    group_id = parent.group_manager.join_group(group_link)
                    if group_id:
                        parent.send_random_message(group_id, "enter")
            case "leave":
                group_id = data.get("group_id")
                if group_id:
                    parent.send_random_message(group_id, "exit")
                    parent.group_manager.leave_group(group_id)

    def start_cleanup(self):
        """
        We start the cleanup thread only on the main instance, i.e. the one that hosts the Signal http server, to avoid multiple instances trying to clean up the same groups.
        """
        if self._is_main_instance():
            self.cleanup_thread = threading.Thread(target=self.cleanup_groups, daemon=True)
            self.cleanup_thread.start()

    def _is_main_instance(self) -> bool:
        """
        Check if we are running on the main instance by checking if the hostname of the Signal server matches the hostname of the current machine.
        """
        hostname = os.uname().nodename
        signal_host = self.host.split("//")[-1].split("/")[0].split(":")[0]
        return hostname == signal_host

    def cleanup_groups(self):
        """
        Cleanup groups that are no longer linked to any session. This method is called periodically to ensure that we don't keep groups around indefinitely.
        """
        # We fetch all groups from the Signal server and check if they are linked to any active session.
        # If not, we leave the group.
        while not self.shutdown_event.is_set():
            try:
                signal_groups = set()
                for depl in self.ingestor.available_deployments:
                    info_container: dict = self.ingestor.redis.get_last(
                        MessageEndpoints.atlas_deployment_info(deployment_name=depl["id"])
                    )
                    info: messages.DeploymentInfoMessage = info_container.get("data")
                    if not info:
                        continue
                    for service in info.messaging_services:
                        if service.service_type != "signal":
                            continue
                        signal_groups.add(service.group_id)
                    if not info.active_session:
                        continue
                    for service in info.active_session.messaging_services:
                        if service.service_type != "signal":
                            continue
                        signal_groups.add(service.group_id)

                groups = self.group_manager.get_all_groups()
                for group in groups:
                    if group.id not in signal_groups:
                        print(
                            f"Leaving group {group.id} as it is no longer linked to any active session."
                        )
                        try:
                            self.group_manager.leave_group(group.id, delete=True)
                        except Exception as exc:
                            print(f"Error leaving group {group.id}:", exc)
            except Exception as exc:
                print("Error during group cleanup:", exc)

            self.shutdown_event.wait(3600)  # Sleep for 1 hour before checking again

    def shutdown(self):
        """
        Shutdown the Signal manager, including the event subscriber and cleanup timer.
        """
        self.subscriber.stop()
        self.shutdown_event.set()
        if self.cleanup_thread:
            self.cleanup_thread.join()
