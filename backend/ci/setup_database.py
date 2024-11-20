import sys
import time

from cassandra.cluster import Cluster

SCYLLA_HOST = "scylla"
SCYLLA_KEYSPACE = "test_bec_atlas"


def wait_for_scylladb(scylla_host: str = SCYLLA_HOST):
    """
    Wait for ScyllaDB to be ready by trying to connect to it.

    Args:
        scylla_host(str): The ScyllaDB host.
    """
    print("Waiting for ScyllaDB to be ready...")
    while True:
        try:
            cluster = Cluster([scylla_host])
            session = cluster.connect()
            print("Connected to ScyllaDB")
            break
        except Exception as e:
            print(f"ScyllaDB not ready yet: {e}")
            time.sleep(5)


def create_keyspace(scylla_host: str = SCYLLA_HOST, keyspace: str = SCYLLA_KEYSPACE):
    """
    Create a new keyspace in ScyllaDB if it does not exist.

    Args:
        scylla_host(str): The ScyllaDB host.
        keyspace(str): The keyspace to create.
    """
    print(f"Creating keyspace '{keyspace}' if not exists...")
    try:
        cluster = Cluster([scylla_host])
        session = cluster.connect()
        session.execute(
            f"""
            CREATE KEYSPACE IF NOT EXISTS {keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
            """
        )
        print(f"Keyspace '{keyspace}' created successfully.")
    except Exception as e:
        print(f"Failed to create keyspace: {e}")
        sys.exit(1)


def setup_database():
    wait_for_scylladb()
    create_keyspace()


if __name__ == "__main__":
    wait_for_scylladb()
    create_keyspace()
