from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SignalRecipientAddress(BaseModel):
    aci: str | None = None
    pni: str | None = None
    number: str | None = None
    username: str | None = None
    uuid: str | None = None


class SignalGroupInfo(BaseModel):
    id: str
    name: str
    groupInviteLink: str | None
    members: list[SignalRecipientAddress]
    pendingMembers: list[SignalRecipientAddress]
    requestingMembers: list[SignalRecipientAddress]
    admins: list[SignalRecipientAddress]
    banned: list[SignalRecipientAddress]
    permissionAddMember: Literal["EVERY_MEMBER", "ONLY_ADMINS"]
    permissionEditDetails: Literal["EVERY_MEMBER", "ONLY_ADMINS"]
    permissionSendMessage: Literal["EVERY_MEMBER", "ONLY_ADMINS"]


class StickerAttachment(BaseModel):
    packId: str
    stickerId: int


class SignalJsonAttachment(BaseModel):
    contentType: str
    filename: str | None = None
    id: str | None = None
    size: int | None = None
    width: int | None = None
    height: int | None = None
    caption: str | None = None
    uploadTimestamp: int | float | None = None


class SignalJsonReaction(BaseModel):
    emoji: str
    targetAuthorNumber: str | None = None
    targetAuthorUuid: str | None = None
    targetSentTimestamp: int | float
    isRemove: bool = False


class SignalJsonMention(BaseModel):
    number: str | None = None
    uuid: str | None = None
    start: int
    length: int


class SignalJsonTextStyle(BaseModel):
    style: str
    start: int
    length: int


class SignalJsonQuote(BaseModel):
    id: int
    authorNumber: str | None = None
    authorUuid: str | None = None
    text: str | None = None
    mentions: list[SignalJsonMention] | None = None
    attachments: list[SignalJsonAttachment] | None = None
    textStyles: list[SignalJsonTextStyle] | None = None


class SignalJsonGroupInfo(BaseModel):
    groupId: str
    groupName: str
    revision: int
    type: Literal["UPDATE", "DELIVER"]


class SignalJsonStoryContext(BaseModel):
    authorNumber: str | None = None
    authorUuid: str | None = None
    sentTimestamp: int | float


class SignalJsonDataMessage(BaseModel):
    timestamp: int | float
    message: str | None
    expiresInSeconds: int = 0
    isExpirationUpdate: bool = False
    viewOnce: bool = False
    reaction: SignalJsonReaction | None = None
    quote: SignalJsonQuote | None = None
    mentions: list[SignalJsonMention] | None = None
    attachments: list[SignalJsonAttachment] | None = None
    sticker: StickerAttachment | None = None
    textStyles: list[SignalJsonTextStyle] | None = None
    groupInfo: SignalJsonGroupInfo | None = None
    storyContext: SignalJsonStoryContext | None = None


class SignalJsonTypingMessage(BaseModel):
    action: Literal["STARTED", "STOPPED"]
    timestamp: int | float
    groupId: str | None = None


class SignalJsonEditMessage(BaseModel):
    targetSentTimestamp: int | float
    dataMessage: SignalJsonDataMessage


class SignalJsonStoryMessage(BaseModel):
    allowsReplies: bool
    groupId: str | None = None
    fileAttachment: SignalJsonAttachment
    textAttachment: dict | None = None


class SignalJsonReadMessage(BaseModel):
    senderNumber: str | None = None
    senderUuid: str | None = None
    timestamp: int | float


class SignalJsonSyncMessage(BaseModel):
    sentMessage: list[SignalJsonDataMessage] | None = None
    sentStoryMessage: list[SignalJsonStoryMessage] | None = None
    blockedNumbers: list[str] | None = None
    blockedGroupIds: list[str] | None = None
    readMessages: list[SignalJsonReadMessage] | None = None
    type: str | None = None


class SignalJsonCallMessage(BaseModel):
    offerMessage: dict | None = None
    answerMessage: dict | None = None
    busyMessage: dict | None = None
    hangupMessage: dict | None = None
    iceUpdateMessages: list[dict] | None = None


class SignalJsonReceiptMessage(BaseModel):
    when: int | float
    isDelivery: bool
    isRead: bool
    isViewed: bool
    timestamps: list[int | float] | None = None


class SignalJsonEnvelope(BaseModel):
    source: str | None = None
    sourceNumber: str | None = None
    sourceUuid: str | None = None
    sourceName: str | None = None
    sourceDevice: int | None = None
    timestamp: int | float
    serverReceivedTimestamp: int | float
    serverDeliveredTimestamp: int | float
    dataMessage: SignalJsonDataMessage | None = None
    editMessage: SignalJsonEditMessage | None = None
    storyMessage: SignalJsonStoryMessage | None = None
    syncMessage: SignalJsonSyncMessage | None = None
    callMessage: SignalJsonCallMessage | None = None
    receiptMessage: SignalJsonReceiptMessage | None = None
    typingMessage: SignalJsonTypingMessage | None = None


class SignalEventMessage(BaseModel):
    envelope: SignalJsonEnvelope
    account: str
