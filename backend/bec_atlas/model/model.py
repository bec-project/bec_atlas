from __future__ import annotations

import uuid
from typing import Any, Literal

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


class AccessProfilePartial(AccessProfile):
    owner_groups: list[str] | None = None
    access_groups: list[str] | None = None


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
    realm_id: str | ObjectId
    name: str
    deployment_key: str = Field(default_factory=lambda: str(uuid.uuid4()))
    active_session_id: str | ObjectId | None = None
    config_templates: list[str | ObjectId] = []


class DeploymentsPartial(MongoBaseModel, AccessProfilePartial):
    realm_id: str | ObjectId | None = None
    name: str | None = None
    deployment_key: str | None = None
    active_session_id: str | ObjectId | None = None
    config_templates: list[str | ObjectId] | None = None


class Realm(MongoBaseModel, AccessProfile):
    realm_id: str
    deployments: list[Deployments | DeploymentsPartial] = []
    name: str


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


class SignalData(AccessProfile, MongoBaseModel):
    """
    Signal data for a device. This is the ophyd signal data,
    aggregated for a single scan. Upon completion of a scan,
    the data is aggregated and stored in this format. If possible,
    the data ingestor will calculate the average, standard deviation,
    min, and max values for the signal.
    """

    scan_id: str | ObjectId | None = None
    device_id: str | ObjectId
    signal_name: str
    data: list[Any]
    timestamps: list[float]
    kind: Literal["hinted", "normal", "config", "omitted"]
    average: float | None = None
    std_dev: float | None = None
    min: float | None = None
    max: float | None = None


class DeviceData(AccessProfile, MongoBaseModel):
    scan_id: str | ObjectId | None = None
    name: str
    device_config_id: str | ObjectId
    signals: list[SignalData]


if __name__ == "__main__":
    out = DeploymentsPartial(realm_id="123")
