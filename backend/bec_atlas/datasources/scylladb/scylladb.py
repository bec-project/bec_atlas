import json
import os
import uuid
from datetime import datetime

from cassandra.cluster import Cluster
from cassandra.cqlengine import columns, connection
from cassandra.cqlengine.management import create_keyspace_simple, sync_table
from pydantic import BaseModel

from bec_atlas.authentication import get_password_hash
from bec_atlas.datasources.scylladb import scylladb_schema as schema


class ScylladbDatasource:
    KEYSPACE = "bec_atlas"

    def __init__(self, config):
        self.config = config
        self.cluster = None
        self.session = None

    def connect(self):
        self.start_client()
        self.load_functional_accounts()

    def start_client(self):
        """
        Start the ScyllaDB client by creating a Cluster object and a Session object.
        """
        hosts = self.config.get("hosts")
        if not hosts:
            raise ValueError("Hosts are not provided in the configuration")

        #
        connection.setup(hosts, self.KEYSPACE, protocol_version=3)
        create_keyspace_simple(self.KEYSPACE, 1)
        self._sync_tables()
        self.cluster = Cluster(hosts)
        self.session = self.cluster.connect()

    def _sync_tables(self):
        """
        Sync the tables with the schema defined in the scylladb_schema.py file.
        """
        sync_table(schema.Realm)
        sync_table(schema.Deployments)
        sync_table(schema.Experiments)
        sync_table(schema.StateCondition)
        sync_table(schema.State)
        sync_table(schema.Session)
        sync_table(schema.Datasets)
        sync_table(schema.DatasetUserData)
        sync_table(schema.Scan)
        sync_table(schema.ScanUserData)
        sync_table(schema.ScanData)
        sync_table(schema.SignalDataInt)
        sync_table(schema.SignalDataFloat)
        sync_table(schema.SignalDataString)
        sync_table(schema.SignalDataBool)
        sync_table(schema.SignalDataBlob)
        sync_table(schema.SignalDataDateTime)
        sync_table(schema.SignalDataUUID)
        sync_table(schema.User)
        sync_table(schema.UserCredentials)

    def load_functional_accounts(self):
        """
        Load the functional accounts to the database.
        """
        functional_accounts_file = os.path.join(
            os.path.dirname(__file__), "functional_accounts.json"
        )
        with open(functional_accounts_file, "r", encoding="utf-8") as file:
            functional_accounts = json.load(file)

        for account in functional_accounts:
            # check if the account already exists in the database
            password_hash = get_password_hash(account.pop("password"))
            result = schema.User.objects.filter(email=account["email"])
            if result.count() > 0:
                continue
            user = schema.User.create(**account)

            schema.UserCredentials.create(user_id=user.user_id, password=password_hash)

    def get(self, table_name: str, filter: str = None, parameters: tuple = None):
        """
        Get the data from the specified table.
        """
        # schema.User.objects.get(email=)
        if filter:
            query = f"SELECT * FROM {self.KEYSPACE}.{table_name} WHERE {filter};"
        else:
            query = f"SELECT * FROM {self.KEYSPACE}.{table_name};"
        if parameters:
            return self.session.execute(query, parameters)
        return self.session.execute(query)

    def post(self, table_name: str, data: BaseModel):
        """
        Post the data to the specified table.

        Args:
            table_name (str): The name of the table to post the data.
            data (BaseModel): The data to be posted.

        """
        query = f"INSERT INTO {self.KEYSPACE}.{table_name} JSON '{data.model_dump_json(exclude_none=True)}';"
        return self.session.execute(query)

    def shutdown(self):
        self.cluster.shutdown()
