import sys
import time

from cassandra.cluster import Cluster

SCYLLA_HOST = "scylla"
SCYLLA_KEYSPACE = "test_bec_atlas"


def wait_for_scylladb():
    print("Waiting for ScyllaDB to be ready...")
    while True:
        try:
            cluster = Cluster([SCYLLA_HOST])
            session = cluster.connect()
            print("Connected to ScyllaDB")
            break
        except Exception as e:
            print(f"ScyllaDB not ready yet: {e}")
            time.sleep(5)


def create_keyspace():
    print(f"Creating keyspace '{SCYLLA_KEYSPACE}' if not exists...")
    try:
        cluster = Cluster([SCYLLA_HOST])
        session = cluster.connect()
        session.execute(
            f"""
            CREATE KEYSPACE IF NOT EXISTS {SCYLLA_KEYSPACE}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
            """
        )
        print(f"Keyspace '{SCYLLA_KEYSPACE}' created successfully.")
    except Exception as e:
        print(f"Failed to create keyspace: {e}")
        sys.exit(1)


if __name__ == "__main__":
    wait_for_scylladb()
    create_keyspace()
