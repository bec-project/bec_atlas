import secrets

import pymongo

from bec_atlas.model import Deployments, Realm, Session


class DemoSetupLoader:

    def __init__(self, config: dict):
        self.config = config
        self.client = pymongo.MongoClient(config.get("host"), config.get("port"))
        self.db = self.client["bec_atlas"]
        self.data = {}

    def load(self):
        self.load_realm()
        self.load_deployments()

    def load_realm(self):
        realm = Realm(
            realm_id="demo_beamline_1",
            name="Demo Beamline 1",
            owner_groups=["admin"],
            access_groups=["auth_user"],
        )
        realm._id = realm.realm_id
        if self.db["realms"].find_one({"realm_id": realm.realm_id}) is None:
            self.db["realms"].insert_one(realm.__dict__)

        realm = Realm(
            realm_id="demo_beamline_2",
            name="Demo Beamline 2",
            owner_groups=["admin"],
            access_groups=["auth_user"],
        )
        realm._id = realm.realm_id
        if self.db["realms"].find_one({"realm_id": realm.realm_id}) is None:
            self.db["realms"].insert_one(realm.__dict__)

    def load_deployments(self):
        deployment = Deployments(
            realm_id="demo_beamline_1",
            name="Demo Deployment 1",
            owner_groups=["admin", "demo"],
            access_groups=["demo"],
        )
        existing_deployment = self.db["deployments"].find_one({"name": deployment.name})
        if existing_deployment is None:
            self.db["deployments"].insert_one(deployment.__dict__)
            existing_deployment = self.db["deployments"].find_one({"name": deployment.name})
        deployment = existing_deployment

        if self.db["deployment_credentials"].find_one({"_id": deployment["_id"]}) is None:
            deployment_credential = {
                "_id": deployment["_id"],
                "credential": secrets.token_urlsafe(32),
            }
            self.db["deployment_credentials"].insert_one(deployment_credential)
            deployment_access = {
                "_id": deployment["_id"],
                "owner_groups": ["admin", "demo"],
                "access_groups": [],
                "user_read_access": [],
                "user_write_access": [],
                "su_read_access": [],
                "su_write_access": [],
                "remote_access": [],
            }
            self.db["deployment_access"].insert_one(deployment_access)

        if self.db["sessions"].find_one({"name": "_default_"}) is None:
            deployment = self.db["deployments"].find_one({"name": deployment.name})
            default_session = Session(
                owner_groups=["admin", "demo"],
                access_groups=["demo"],
                deployment_id=deployment["_id"],
                name="_default_",
            )
            self.db["sessions"].insert_one(default_session.model_dump(exclude_none=True))


if __name__ == "__main__":
    loader = DemoSetupLoader({"host": "localhost", "port": 27017})
    loader.load()
