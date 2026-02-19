import os
import secrets

import pymongo
import yaml
from bec_lib import messages

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
            realm.id = realm.realm_id

            # Check if the realm already exists in the database and insert if not
            if self.db["realms"].find_one({"realm_id": realm.realm_id}) is None:
                print(f"Inserting realm: {realm.realm_id}")
                self.db["realms"].insert_one(realm.model_dump(by_alias=True))

    def _load_deployments(self):
        for realm_name, realm_data in self._data.items():
            for depl_url, depl in realm_data.get("deployments", {}).items():
                deployment_owner_groups = depl.get("deployment_access", []) + ["admin"]
                deployment = Deployments(
                    realm_id=realm_name,
                    name=depl_url,
                    owner_groups=deployment_owner_groups,
                    access_groups=["auth_user"],
                    messaging_config=messages.MessagingConfig(
                        signal=messages.MessagingServiceScopeConfig(enabled=True, default=None),
                        scilog=messages.MessagingServiceScopeConfig(enabled=True, default=None),
                        teams=messages.MessagingServiceScopeConfig(enabled=False, default=None),
                    ),
                )

                # Check if the deployment already exists in the database and insert if not
                existing_deployment = self.db["deployments"].find_one(
                    {"name": deployment.name, "realm_id": deployment.realm_id}
                )
                if existing_deployment is None:
                    print(f"Inserting deployment: {deployment.name}")
                    self.db["deployments"].insert_one(deployment.model_dump(exclude_none=True))
                    existing_deployment = self.db["deployments"].find_one(
                        {"name": deployment.name, "realm_id": deployment.realm_id}
                    )
                else:
                    # Update the owner and access groups if necessary
                    if (
                        existing_deployment["access_groups"] != deployment.access_groups
                        or existing_deployment["owner_groups"] != deployment.owner_groups
                    ):
                        print(f"Updating deployment access groups: {deployment.name}")
                        self.db["deployments"].update_one(
                            {"_id": existing_deployment["_id"]},
                            {
                                "$set": {
                                    "access_groups": deployment.access_groups,
                                    "owner_groups": deployment.owner_groups,
                                }
                            },
                        )

                deployment = Deployments(**existing_deployment)

                # Create default session if it does not exist
                existing_default_session = self.db["sessions"].find_one(
                    {"name": "_default_", "deployment_id": deployment.id}
                )
                session_owner_groups = depl.get("experiment_access", []) + ["admin"]
                if existing_default_session is None:
                    default_session = Session(
                        owner_groups=session_owner_groups,
                        access_groups=[],
                        deployment_id=deployment.id,
                        name="_default_",
                    )
                    self.db["sessions"].insert_one(default_session.model_dump(exclude_none=True))
                else:
                    # Patch the existing session if necessary
                    if (
                        existing_default_session["access_groups"] != []
                        or existing_default_session["owner_groups"] != session_owner_groups
                    ):
                        print(
                            f"Updating the access groups for the default session: {deployment.name}"
                        )
                        self.db["sessions"].update_one(
                            {"_id": existing_default_session["_id"]},
                            {"$set": {"access_groups": [], "owner_groups": session_owner_groups}},
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
                        "owner_groups": ["admin"] + depl.get("deployment_access", []),
                        "access_groups": [],
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
                    if existing_deployment_access[
                        "access_groups"
                    ] != [] or existing_deployment_access["owner_groups"] != ["admin"] + depl.get(
                        "deployment_access", []
                    ):
                        print(f"Updating access groups of DeploymentAccess: {deployment.name}")
                        self.db["deployment_access"].update_one(
                            {"_id": existing_deployment_access["_id"]},
                            {
                                "$set": {
                                    "access_groups": [],
                                    "owner_groups": ["admin"] + depl.get("deployment_access", []),
                                }
                            },
                        )

                # Create messaging_config if it does not exist
                if not existing_deployment.get("messaging_config"):
                    config = messages.MessagingConfig(
                        signal=messages.MessagingServiceScopeConfig(enabled=True, default=None),
                        scilog=messages.MessagingServiceScopeConfig(
                            enabled=True, default="default"
                        ),
                        teams=messages.MessagingServiceScopeConfig(enabled=False, default=None),
                    )
                    print(f"Adding messaging config to deployment: {deployment.name}")
                    self.db["deployments"].update_one(
                        {"_id": deployment.id},
                        {"$set": {"messaging_config": config.model_dump(exclude_none=True)}},
                    )


if __name__ == "__main__":  # pragma: no cover
    import glob

    default_path = os.path.abspath(os.path.dirname(os.path.dirname((__file__))))
    loader = DeploymentIngestor({"host": "localhost", "port": 27017})
    realm_files = glob.glob(os.path.join(default_path, "deployment/realms/*.yaml"))
    for realm_file in realm_files:
        with open(realm_file, "r") as file:
            data = yaml.safe_load(file)
        loader.load(data)
