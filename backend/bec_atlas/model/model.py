from __future__ import annotations

from typing import Any, Literal, Type, TypeAlias, TypeVar

from bec_lib import messages
from bec_lib.atlas_models import make_all_fields_optional
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

T = TypeVar("T")


def make_fields_optional_with_relations(model: Type[T], model_name: str) -> Type[T]:
    """
    Create a partial model with all fields optional while preserving __relations__.

    Args:
        model: The source model class
        model_name: Name for the new partial model

    Returns:
        A new model class with all fields optional and __relations__ copied
    """
    partial_model = make_all_fields_optional(model, model_name)

    # Copy __relations__ if it exists on the source model
    if hasattr(model, "__relations__"):
        partial_model.__relations__ = model.__relations__

    return partial_model


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


class Relation(BaseModel):
    reference_collection: str = Field(
        description="The name of the MongoDB collection that this relation references."
    )
    reference_model: Type[BaseModel] = Field(
        description="The model class that this relation references."
    )
    local_field: str = Field(
        description=(
            "The field in the local model that holds the reference value. "
            "For outbound relationships, this is typically the foreign key. "
            "For inbound relationships, this is typically the primary key (often 'id'). "
            "Note that this is not the name of the resolved field. The resolved field name is "
            "determined by the key in the __relations__ dict of the model."
        )
    )
    foreign_field: str = Field(
        description=(
            "The field in the foreign model that holds the reference value. "
            "For outbound relationships, this is typically the primary key (often 'id'). "
            "For inbound relationships, this is typically the foreign key, e.g. 'parent_id'."
        )
    )
    relationship: Literal["1-1", "1-N"] = Field(
        description=(
            "The type of relationship. '1-1' indicates a one-to-one relationship, "
            "'1-N' indicates a one-to-many relationship."
        )
    )
    direction: Literal["outbound", "inbound"] = Field(
        description=(
            "Direction of the relationship from the perspective of the local model. "
            "Outbound means the local model holds a reference to the foreign model, "
            "inbound means the foreign model holds a reference to the local model."
        )
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


Relations: TypeAlias = dict[str, Relation]


class MongoBaseModel(BaseModel):
    id: str | ObjectId | None = Field(default=None, alias="_id")

    model_config = ConfigDict(
        populate_by_name=True, arbitrary_types_allowed=True, json_encoders={ObjectId: str}
    )

    __relations__: Relations = {}

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


class ScanUserData(BaseModel):
    """
    ScanUserData is an extension to the Scan model and is access controlled through
    the scan's user permissions. It cannot be queried independently of the scan.

    It is designed to encapsulate all user-specific data related to a scan, such as
    user ratings and comments.
    """

    name: str | None = None
    user_rating: int | None = None
    system_rating: int | None = None
    user_comments: str | None = None
    system_comments: str | None = None
    preview: str | None = None


ScanUserDataPartial = make_fields_optional_with_relations(ScanUserData, "ScanUserDataPartial")


class ScanStatus(MongoBaseModel, AccessProfile, messages.ScanStatusMessage):
    session_id: str | ObjectId | None = None
    user_data: ScanUserData | None = None
    file_path: str | None = None
    start_time: float | None = None
    end_time: float | None = None

    @field_validator("session_id", mode="before")
    def normalize_session_id(cls, v: str) -> ObjectId | None:
        if isinstance(v, str):
            return ObjectId(v)
        return v


ScanStatusPartial = make_fields_optional_with_relations(ScanStatus, "ScanStatusPartial")


class UserCredentials(MongoBaseModel, AccessProfile):
    user_id: str | ObjectId
    password: str

    @field_validator("user_id", mode="before")
    def normalize_user_id(cls, v: str) -> ObjectId:
        if isinstance(v, str):
            return ObjectId(v)
        return v


class User(MongoBaseModel, AccessProfile):
    email: str
    groups: list[str]
    first_name: str
    last_name: str
    username: str | None = None


UserPartial = make_fields_optional_with_relations(User, "UserPartial")


class UserInfo(BaseModel):
    email: str
    token: str


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


DeploymentAccessPartial = make_fields_optional_with_relations(
    DeploymentAccess, "DeploymentAccessPartial"
)


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

    deployment_id: str | ObjectId
    username: str
    passwords: dict[str, str] = {}
    categories: list[str] = []
    keys: list[str] = []
    channels: list[str] = []
    commands: list[str] = []
    profile: str = ""

    @field_validator("deployment_id", mode="before")
    def normalize_deployment_id(cls, v: str) -> ObjectId:
        if isinstance(v, str):
            return ObjectId(v)
        return v


BECAccessProfilePartial = make_fields_optional_with_relations(
    BECAccessProfile, "BECAccessProfilePartial"
)


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


ExperimentPartial = make_fields_optional_with_relations(Experiment, "ExperimentPartial")


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


class MessagingService(MongoBaseModel, AccessProfile, messages.MessagingService):
    parent_id: str | ObjectId

    @field_validator("parent_id", mode="before")
    def normalize_parent_id(cls, v: str) -> ObjectId:
        if isinstance(v, str):
            return ObjectId(v)
        return v


MessagingServicePartial = make_fields_optional_with_relations(
    MessagingService, "MessagingServicePartial"
)


class SignalServiceInfo(MessagingServicePartial, messages.SignalServiceInfo): ...


SignalServiceInfoPartial = make_fields_optional_with_relations(
    SignalServiceInfo, "SignalServiceInfoPartial"
)


class SciLogServiceInfo(MessagingServicePartial, messages.SciLogServiceInfo): ...


SciLogServiceInfoPartial = make_fields_optional_with_relations(
    SciLogServiceInfo, "SciLogServiceInfoPartial"
)


class TeamsServiceInfo(MessagingServicePartial, messages.TeamsServiceInfo): ...


TeamsServiceInfoPartial = make_fields_optional_with_relations(
    TeamsServiceInfo, "TeamsServiceInfoPartial"
)


AvailableMessagingServiceInfo: TypeAlias = SignalServiceInfo | SciLogServiceInfo | TeamsServiceInfo
AvailableMessagingServiceInfoPartial = (
    SignalServiceInfoPartial | SciLogServiceInfoPartial | TeamsServiceInfoPartial
)


class MergedMessagingServiceInfo(
    SignalServiceInfoPartial, SciLogServiceInfoPartial, TeamsServiceInfoPartial
): ...


class DeviceConfig(MongoBaseModel, AccessProfile):
    device_name: str
    readout_priority: Literal["monitored", "baseline", "on_request", "async", "continuous"]
    device_config: dict
    device_class: str
    device_hash: str
    tags: list[str] = []
    software_trigger: bool


class DeviceHash(MongoBaseModel, AccessProfile):
    realm_id: str
    name: str
    description: str = ""
    hash_config: dict
    device_tags: list[str] = []
    variant_tags: list[str] = []
    latest_config: str | None = None
    reference_config: str | None = None


class DeviceConfigCollection(MongoBaseModel, AccessProfile):
    session_id: str | ObjectId
    configs: list[str] = []

    @field_validator("session_id", mode="before")
    @classmethod
    def normalize_session_id(cls, v: str) -> ObjectId:
        if isinstance(v, str):
            return ObjectId(v)
        return v


class Session(MongoBaseModel, AccessProfile, messages.SessionInfoMessage):
    """
    A session represents a logical unit of work within a deployment. Most commonly,
    there is only a single session per Experiment.
    """

    deployment_id: str | ObjectId
    name: str
    experiment_id: str | None = None
    experiment: Experiment | None = None
    device_config_collections: list[DeviceConfigCollection] = []
    messaging_services: list[AvailableMessagingServiceInfo] = []

    @field_validator("deployment_id", mode="before")
    @classmethod
    def normalize_deployment_id(cls, v: str) -> ObjectId:
        if isinstance(v, str):
            return ObjectId(v)
        return v

    __relations__: Relations = {
        "experiment": Relation(
            reference_collection="experiments",
            reference_model=ExperimentPartial,
            local_field="experiment_id",
            foreign_field="_id",
            relationship="1-1",
            direction="outbound",
        ),
        "messaging_services": Relation(
            reference_collection="messaging_services",
            reference_model=MessagingServicePartial,
            local_field="_id",
            foreign_field="parent_id",
            relationship="1-N",
            direction="inbound",
        ),
    }


SessionPartial = make_fields_optional_with_relations(Session, "SessionPartial")


class DatasetUserData(AccessProfile):
    """
    DatasetUserData is an extension to the Dataset model and is access controlled through
    the dataset's user permissions. It cannot be queried independently of the dataset.

    It is designed to encapsulate all user-specific data related to a dataset, such as
    user ratings and comments.
    """

    dataset_id: str
    name: str

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class Dataset(MongoBaseModel, AccessProfile):
    realm_id: str
    name: str
    description: str
    user_data: DatasetUserData | None = None
    scans: list[ScanStatus] = []

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


DatasetPartial = make_fields_optional_with_relations(Dataset, "DatasetPartial")


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


class Deployments(MongoBaseModel, AccessProfile):
    realm_id: str
    name: str
    active_session_id: str | ObjectId | None = None
    active_session: Session | None = None
    config_templates: list[str | ObjectId] = []
    messaging_config: messages.MessagingConfig | None = None
    messaging_services: list[AvailableMessagingServiceInfo] = []

    __relations__: Relations = {
        "active_session": Relation(
            reference_collection="sessions",
            reference_model=SessionPartial,
            local_field="active_session_id",
            foreign_field="_id",
            relationship="1-1",
            direction="outbound",
        ),
        "messaging_services": Relation(
            reference_collection="messaging_services",
            reference_model=MessagingServicePartial,
            local_field="_id",
            foreign_field="parent_id",
            relationship="1-N",
            direction="inbound",
        ),
    }


DeploymentsPartial = make_fields_optional_with_relations(Deployments, "DeploymentsPartial")


class Realm(MongoBaseModel, AccessProfile):
    realm_id: str
    deployments: list[Deployments | DeploymentsPartial] = []  # type: ignore
    name: str
    xname: str | None = None
    managers: list[str] = []

    __relations__: Relations = {
        "deployments": Relation(
            reference_collection="deployments",
            reference_model=DeploymentsPartial,
            local_field="realm_id",
            foreign_field="realm_id",
            relationship="1-N",
            direction="inbound",
        )
    }


RealmPartial = make_fields_optional_with_relations(Realm, "RealmPartial")


class DeviceData(AccessProfile, MongoBaseModel):
    scan_id: str | None = None
    name: str
    device_config_id: str
    signals: list[SignalData]


if __name__ == "__main__":
    out = DeploymentsPartial(realm_id="123")
