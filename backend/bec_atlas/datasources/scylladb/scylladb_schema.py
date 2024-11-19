import uuid

from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model


class User(Model):
    email = columns.Text(primary_key=True)
    user_id = columns.UUID(default=uuid.uuid4())
    first_name = columns.Text()
    last_name = columns.Text()
    groups = columns.Set(columns.Text)
    created_at = columns.DateTime()
    updated_at = columns.DateTime()


class UserCredentials(Model):
    user_id = columns.UUID(primary_key=True)
    password = columns.Text()


class Realm(Model):
    realm_id = columns.Text(primary_key=True)
    deployment_id = columns.Text(primary_key=True)
    name = columns.Text()


class Deployments(Model):
    realm_id = columns.Text(primary_key=True)
    deployment_id = columns.Text(primary_key=True)
    name = columns.Text()
    active_session_id = columns.UUID()


class Experiments(Model):
    realm_id = columns.Text(primary_key=True)
    pgroup = columns.Text(primary_key=True)
    proposal = columns.Text()
    text = columns.Text()


class StateCondition(Model):
    realm_id = columns.Text(primary_key=True)
    name = columns.Text(primary_key=True)
    description = columns.Text()
    device = columns.Text()
    signal_value = columns.Text()
    signal_type = columns.Text()
    tolerance = columns.Text()


class State(Model):
    realm_id = columns.Text(primary_key=True)
    name = columns.Text(primary_key=True)
    description = columns.Text()
    conditions = columns.List(columns.Text)


class Session(Model):
    realm_id = columns.Text(primary_key=True)
    session_id = columns.UUID(primary_key=True)
    config = columns.Text()


class Datasets(Model):
    session_id = columns.UUID(primary_key=True)
    dataset_id = columns.UUID(primary_key=True)
    scan_id = columns.UUID()


class DatasetUserData(Model):
    dataset_id = columns.UUID(primary_key=True)
    name = columns.Text()
    rating = columns.Integer()
    comments = columns.Text()
    preview = columns.Blob()


class Scan(Model):
    session_id = columns.UUID(primary_key=True)
    scan_id = columns.UUID(primary_key=True)
    scan_number = columns.Integer()
    name = columns.Text()
    scan_class = columns.Text()
    parameters = columns.Text()
    start_time = columns.DateTime()
    end_time = columns.DateTime()
    exit_status = columns.Text()


class ScanUserData(Model):
    scan_id = columns.UUID(primary_key=True)
    name = columns.Text()
    rating = columns.Integer()
    comments = columns.Text()
    preview = columns.Blob()


class ScanData(Model):
    scan_id = columns.UUID(primary_key=True)
    device_name = columns.Text(primary_key=True)
    signal_name = columns.Text(primary_key=True)
    shape = columns.List(columns.Integer)
    dtype = columns.Text()


class SignalDataBase(Model):
    realm_id = columns.Text(partition_key=True)
    signal_name = columns.Text(partition_key=True)
    scan_id = columns.UUID(primary_key=True)
    index = columns.Integer(primary_key=True)


class SignalDataInt(SignalDataBase):
    data = columns.Integer()


class SignalDataFloat(SignalDataBase):
    data = columns.Float()


class SignalDataString(SignalDataBase):
    data = columns.Text()


class SignalDataBlob(SignalDataBase):
    data = columns.Blob()


class SignalDataBool(SignalDataBase):
    data = columns.Boolean()


class SignalDataDateTime(SignalDataBase):
    data = columns.DateTime()


class SignalDataUUID(SignalDataBase):
    data = columns.UUID()
