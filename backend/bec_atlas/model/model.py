import uuid
from typing import Literal

from bec_lib import messages
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class MongoBaseModel(BaseModel):
    id: str | ObjectId | None = Field(default=None, alias="_id")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    @field_serializer("id")
    def serialize_id(self, id: str | ObjectId):
        if isinstance(id, ObjectId):
            return str(id)
        return id


class AccessProfile(BaseModel):
    owner_groups: list[str]
    access_groups: list[str] = []


class ScanStatus(MongoBaseModel, AccessProfile, messages.ScanStatusMessage): ...


class UserCredentials(MongoBaseModel, AccessProfile):
    user_id: str | ObjectId
    password: str


class User(MongoBaseModel, AccessProfile):
    email: str
    groups: list[str]
    first_name: str
    last_name: str


class UserInfo(BaseModel):
    email: str
    groups: list[str]


class Deployments(MongoBaseModel, AccessProfile):
    realm_id: str
    name: str
    deployment_key: str = Field(default_factory=lambda: str(uuid.uuid4()))
    active_session_id: str | None = None


class Experiments(AccessProfile):
    realm_id: str
    pgroup: str
    proposal: str
    text: str

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class StateCondition(AccessProfile):
    realm_id: str
    name: str
    description: str
    device: str
    signal_value: str
    signal_type: str
    tolerance: str

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class State(AccessProfile):
    realm_id: str
    name: str
    description: str
    conditions: list[str]

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class Session(MongoBaseModel, AccessProfile):
    deployment_id: str | ObjectId
    name: str


class Realm(MongoBaseModel, AccessProfile):
    realm_id: str
    deployments: list[Deployments] = []
    name: str


class Datasets(AccessProfile):
    realm_id: str
    dataset_id: str
    name: str
    description: str

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class DatasetUserData(AccessProfile):
    dataset_id: str
    name: str

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class ScanUserData(AccessProfile):
    scan_id: str
    name: str
    rating: int
    comments: str
    preview: bytes

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class DeviceConfig(AccessProfile):
    device_name: str
    readout_priority: Literal["monitored", "baseline", "on_request", "async", "continuous"]
    device_config: dict
    device_class: str
    tags: list[str] = []
    software_trigger: bool


class SignalData(AccessProfile):
    scan_id: str
    device_id: str
    device_name: str
    signal_name: str
    data: float | int | str | bool | bytes | dict | list | None
    timestamp: float
    kind: Literal["hinted", "omitted", "normal", "config"]


class DeviceData(AccessProfile):
    scan_id: str | None
    device_name: str
    device_config_id: str
    signals: list[SignalData]
