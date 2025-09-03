from __future__ import annotations

from typing import Any, Literal, Type, TypeVar

from bec_lib import messages
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, create_model, field_serializer, field_validator

T = TypeVar("T")


XNAME_MAPPING = {
    "x01da": ("Debye",),
    "x02da": ("S-TOMCAT", "TOMCAT"),
    "x02sa": ("I-TOMCAT",),
    "x03da": ("PEARL",),
    "x03ma": ("ADRESS", "ADRESS-RIXS", "ADRESS-SX-ARPES"),
    "x04db": ("VUV",),
    "x04sa": ("ADDAMS", "MS-Powder", "MS-Surf-Diffr"),
    "x05la": ("microXAS", "Micro-XAS-FEMTO", "Micro-XAS"),
    "x06da": ("PXIII",),
    "x06sa": ("PXI",),
    "x07da": ("PolLux", "NanoXAS"),
    "x07db": ("ISS", "In Situ Spectroscopy"),
    "x07ma": ("X-Treme", "XTreme"),
    "x07mb": ("Phoenix",),
    "x09la": ("SIS", "SIS-ULTRA", "SIS-Cophee"),
    "x09lb": ("XIL", "XIL-II"),
    "x10da": ("SuperXAS", "Super-XAS"),
    "x10sa": ("PXII",),
    "x11ma": ("SIM",),
    "x12sa": ("cSAXS",),
}

ALIAS_TO_CANONICAL = {}
for xname, aliases in XNAME_MAPPING.items():
    canonical = aliases[0]
    # map all aliases
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical
    # map xname itself
    ALIAS_TO_CANONICAL[xname.lower()] = canonical

_available_xnames = set()


def is_valid_beamline_name(name: str) -> bool:
    """Check if the given name is a valid beamline name."""
    return name.lower() in ALIAS_TO_CANONICAL


def xname_to_canonical(name: str) -> str | None:
    """Convert a beamline name to its canonical form."""
    return ALIAS_TO_CANONICAL.get(name.lower())


def name_to_xname(name: str) -> str | None:
    """Convert a canonical beamline name to its xname form."""
    for xname, names in XNAME_MAPPING.items():
        if name in names:
            return xname
    return None


def make_all_fields_optional(model: Type[T], model_name: str) -> Type[T]:
    """Convert all fields in a Pydantic model to Optional."""

    # create a dictionary of fields with the same name but with the type Optional[field]
    # and a default value of None
    fields = {}

    for name, field in model.__fields__.items():
        fields[name] = (field.annotation, None)

    return create_model(model_name, **fields, __config__=model.model_config)


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


class ScanStatus(MongoBaseModel, AccessProfile, messages.ScanStatusMessage):
    user_data: ScanUserData | None = None


ScanStatusPartial = make_all_fields_optional(ScanStatus, "ScanStatusPartial")


class UserCredentials(MongoBaseModel, AccessProfile):
    user_id: str | ObjectId
    password: str


class User(MongoBaseModel, AccessProfile):
    email: str
    groups: list[str]
    first_name: str
    last_name: str
    username: str | None = None


class UserInfo(BaseModel):
    email: str
    token: str


class Deployments(MongoBaseModel, AccessProfile):
    realm_id: str
    name: str
    active_session_id: str | ObjectId | None = None
    config_templates: list[str | ObjectId] = []


class DeploymentsPartial(MongoBaseModel, AccessProfilePartial):
    realm_id: str | None = None
    name: str | None = None
    active_session_id: str | ObjectId | None = None
    config_templates: list[str | ObjectId] | None = None


class DeploymentCredential(MongoBaseModel):
    credential: str


class DeploymentAccess(MongoBaseModel, AccessProfile):
    """
    The DeploymentAccess model is used to store the access control
    lists for the deployment. The access control lists are used to
    control access to the BEC deployment and contain either user
    or group names.
    Once the access control lists are updated, the corresponding
    BECAccessProfiles for this deployment are updated to reflect
    the changes.

    Owner: beamline staff
    """

    user_read_access: list[str] = []
    user_write_access: list[str] = []
    su_read_access: list[str] = []
    su_write_access: list[str] = []
    remote_read_access: list[str] = []
    remote_write_access: list[str] = []


class BECAccessProfile(MongoBaseModel, AccessProfile):
    """
    The BECAccessProfile model is used to store the Redis ACL config
    for BEC of a user. The username can be either a user or a group.
    The config fields (categories, keys, channels, commands) are determined
    based on the access level given through the corresponding DeploymentAccess
    document.

    Owner: admin
    Access: user or group matching the username

    """

    deployment_id: str
    username: str
    passwords: dict[str, str] = {}
    categories: list[str] = []
    keys: list[str] = []
    channels: list[str] = []
    commands: list[str] = []
    profile: str = ""


class Realm(MongoBaseModel, AccessProfile):
    realm_id: str
    deployments: list[Deployments | DeploymentsPartial] = []
    name: str
    xname: str | None = None
    managers: list[str] = []


class Experiment(MongoBaseModel, AccessProfile):
    realm_id: str
    proposal: str
    title: str
    firstname: str
    lastname: str
    email: str
    account: str
    pi_firstname: str
    pi_lastname: str
    pi_email: str
    pi_account: str
    eaccount: str
    pgroup: str
    abstract: str
    schedule: list[dict] | None = None
    proposal_submitted: str | None = None
    proposal_expire: str | None = None
    proposal_status: str | None = None
    delta_last_schedule: int | None = None
    mainproposal: str | None = None

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    @field_validator("realm_id", mode="before")
    @classmethod
    def normalize_beamline(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        key = v.lower()
        return ALIAS_TO_CANONICAL.get(key, v)


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
    deployment_id: str
    name: str


SessionPartial = make_all_fields_optional(Session, "SessionPartial")


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


class ScanUserData(BaseModel):
    name: str | None = None
    user_rating: int | None = None
    system_rating: int | None = None
    user_comments: str | None = None
    system_comments: str | None = None
    preview: str | None = None


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

    scan_id: str | None = None
    device_id: str
    signal_name: str
    data: list[Any]
    timestamps: list[float]
    kind: Literal["hinted", "normal", "config", "omitted"]
    average: float | None = None
    std_dev: float | None = None
    min: float | None = None
    max: float | None = None


class DeviceData(AccessProfile, MongoBaseModel):
    scan_id: str | None = None
    name: str
    device_config_id: str
    signals: list[SignalData]


if __name__ == "__main__":
    out = DeploymentsPartial(realm_id="123")
