import os


def export_mongodb_data(host: str, port: int):
    """Export data from MongoDB to a JSON file."""

    collections = [
        "bec_access_profiles",
        "deployment_access",
        "deployment_credentials",
        "deployments",
        "fs.chunks",
        "fs.files",
        "scans",
        "sessions",
        "user_credentials",
        "users",
    ]

    current_dir = os.path.dirname(os.path.abspath(__file__))

    for collection in collections:
        os.system(
            f"mongoexport --host {host} --port {port} --db bec_atlas --collection {collection} --jsonArray --out {current_dir}/test_data/bec_atlas.{collection}.json"
        )


if __name__ == "__main__":
    export_mongodb_data("localhost", 27017)
