import sys
import time

from cassandra.cluster import Cluster, Session

SCYLLA_HOST = "scylla"
SCYLLA_PORT = 9042
SCYLLA_KEYSPACE = "bec_atlas"


def wait_for_scylladb(scylla_host: str = SCYLLA_HOST, scylla_port: int = SCYLLA_PORT):
    """
    Wait for ScyllaDB to be ready by trying to connect to it.

    Args:
        scylla_host(str): The ScyllaDB host.
    """
    print("Waiting for ScyllaDB to be ready...")
    print(f"ScyllaDB host: {scylla_host}")
    print(f"ScyllaDB port: {scylla_port}")
    while True:
        try:
            cluster = Cluster([(scylla_host, scylla_port)])
            # cluster = Cluster([scylla_host])
            session = cluster.connect()
            print("Connected to ScyllaDB")
            return session
        except Exception as e:
            print(f"ScyllaDB not ready yet: {e}")
            time.sleep(5)


def create_keyspace(session: Session, keyspace: str = SCYLLA_KEYSPACE):
    """
    Create a new keyspace in ScyllaDB if it does not exist.

    Args:
        scylla_host(str): The ScyllaDB host.
        keyspace(str): The keyspace to create.
    """
    print(f"Creating keyspace '{keyspace}' if not exists...")
    try:
        # drop the keyspace if it exists
        session.execute(f"DROP KEYSPACE IF EXISTS {keyspace}")
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


def setup_database(host: str = SCYLLA_HOST, port: int = SCYLLA_PORT):
    session = wait_for_scylladb(scylla_host=host, scylla_port=port)
    create_keyspace(session)


if __name__ == "__main__":
    setup_database()
