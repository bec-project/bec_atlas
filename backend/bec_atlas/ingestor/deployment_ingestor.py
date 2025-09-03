import os
import secrets

import pymongo
import yaml

from bec_atlas.model import Deployments, Realm, Session


class DeploymentIngestor:
    """
    The DeploymentIngestor class is responsible for loading deployment data into the MongoDB database.
    It is executed as part of the deployment procedure, loading the deployment file and creating the
    database entries for realms and deployments as well as the default session if it does not exist.
    """

    def __init__(self, config: dict):
        self.config = config
        self.client = pymongo.MongoClient(config.get("host"), config.get("port"))
        self.db = self.client["bec_atlas"]
        self._data = {}

    def load(self, data):
        self._data = data
        self._load_realm()
        self._load_deployments()

    def _load_realm(self):
        for realm_name, realm_data in self._data.items():
            realm = Realm(
                realm_id=realm_name,
                name=realm_name,
                xname=realm_data.get("xname"),
                owner_groups=["admin"],
                access_groups=["auth_user"],
                managers=realm_data.get("managers", []),
            )
            realm._id = realm.realm_id

            # Check if the realm already exists in the database and insert if not
            if self.db["realms"].find_one({"realm_id": realm.realm_id}) is None:
                print(f"Inserting realm: {realm.realm_id}")
                self.db["realms"].insert_one(realm.__dict__)

    def _load_deployments(self):
        for realm_name, realm_data in self._data.items():
            for depl_url, depl in realm_data.get("deployments", {}).items():
                deployment = Deployments(
                    realm_id=realm_name,
                    name=depl_url,
                    owner_groups=["admin"],
                    access_groups=depl.get("deployment_access", []),
                )

                # Check if the deployment already exists in the database and insert if not
                existing_deployment = self.db["deployments"].find_one({"name": deployment.name})
                if existing_deployment is None:
                    print(f"Inserting deployment: {deployment.name}")
                    self.db["deployments"].insert_one(deployment.__dict__)
                    existing_deployment = self.db["deployments"].find_one({"name": deployment.name})
                else:
                    # Update the access groups if necessary
                    if existing_deployment["access_groups"] != deployment.access_groups:
                        print(f"Updating deployment access groups: {deployment.name}")
                        self.db["deployments"].update_one(
                            {"_id": existing_deployment["_id"]},
                            {"$set": {"access_groups": deployment.access_groups}},
                        )
                deployment = Deployments(**existing_deployment)

                # Create default session if it does not exist
                existing_default_session = self.db["sessions"].find_one(
                    {"name": "_default_", "deployment_id": str(deployment.id)}
                )
                if existing_default_session is None:
                    default_session = Session(
                        owner_groups=depl.get("deployment_access", []),
                        access_groups=depl.get("experiment_access", []),
                        deployment_id=str(deployment.id),
                        name="_default_",
                    )
                    self.db["sessions"].insert_one(default_session.model_dump(exclude_none=True))
                else:
                    # Patch the existing session if necessary
                    if existing_default_session["access_groups"] != depl.get(
                        "experiment_access", []
                    ) or existing_default_session["owner_groups"] != depl.get(
                        "deployment_access", []
                    ):
                        print(
                            f"Updating the access groups for the default session: {deployment.name}"
                        )
                        self.db["sessions"].update_one(
                            {"_id": existing_default_session["_id"]},
                            {
                                "$set": {
                                    "access_groups": depl.get("experiment_access", []),
                                    "owner_groups": depl.get("deployment_access", []),
                                }
                            },
                        )

                # Create deployment credentials if they do not exist
                existing_deployment_credential = self.db["deployment_credentials"].find_one(
                    {"_id": deployment.id}
                )
                if existing_deployment_credential is None:
                    deployment_credential = {
                        "_id": deployment.id,
                        "credential": secrets.token_urlsafe(32),
                    }
                    self.db["deployment_credentials"].insert_one(deployment_credential)

                # Create deployment access if it does not exist
                existing_deployment_access = self.db["deployment_access"].find_one(
                    {"_id": deployment.id}
                )
                if existing_deployment_access is None:
                    deployment_access = {
                        "_id": deployment.id,
                        "owner_groups": ["admin"],
                        "access_groups": depl.get("deployment_access", []),
                        "user_read_access": [],
                        "user_write_access": [],
                        "su_read_access": [],
                        "su_write_access": [],
                        "remote_read_access": [],
                        "remote_write_access": [],
                    }
                    self.db["deployment_access"].insert_one(deployment_access)
                else:
                    # Patch the access groups if necessary
                    if existing_deployment_access["access_groups"] != depl.get(
                        "deployment_access", []
                    ):
                        print(f"Updating access groups of DeploymentAccess: {deployment.name}")
                        self.db["deployment_access"].update_one(
                            {"_id": existing_deployment_access["_id"]},
                            {"$set": {"access_groups": depl.get("deployment_access", [])}},
                        )


if __name__ == "__main__":

    default_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname((__file__)))))
    loader = DeploymentIngestor({"host": "localhost", "port": 27017})
    with open(os.path.join(default_path, "utils/sls_deployments.yaml"), "r") as file:
        data = yaml.safe_load(file)
    loader.load(data)
