from bson import ObjectId

from bec_atlas.utils.migrations.migration_base import BaseMigration


class MigrateMongoIds(BaseMigration):
    """
    Migration to transform string IDs to ObjectIds for proper MongoDB referencing.
    Converts deployment_id, session_id, active_session_id, and parent_id fields.
    """

    def transform_deployment_id(self):
        for collection in ["bec_access_profiles", "sessions"]:
            for doc in self.datasource.db[collection].find({}):
                if "deployment_id" in doc and isinstance(doc["deployment_id"], str):
                    self.datasource.db[collection].update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"deployment_id": ObjectId(doc["deployment_id"])}},
                    )

    def transform_session_id(self):
        for collection in ["scans", "deployments"]:
            for doc in self.datasource.db[collection].find({}):
                if "session_id" in doc and isinstance(doc["session_id"], str):
                    self.datasource.db[collection].update_one(
                        {"_id": doc["_id"]}, {"$set": {"session_id": ObjectId(doc["session_id"])}}
                    )
                if "active_session_id" in doc and isinstance(doc["active_session_id"], str):
                    self.datasource.db[collection].update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"active_session_id": ObjectId(doc["active_session_id"])}},
                    )

    def transform_parent_id(self):
        for collection in ["messaging_services"]:
            for doc in self.datasource.db[collection].find({}):
                if "parent_id" in doc and isinstance(doc["parent_id"], str):
                    self.datasource.db[collection].update_one(
                        {"_id": doc["_id"]}, {"$set": {"parent_id": ObjectId(doc["parent_id"])}}
                    )

    def run(self):
        """
        Execute the migration: transform all ID fields from strings to ObjectIds.
        """
        self.transform_deployment_id()
        self.transform_session_id()
        self.transform_parent_id()


if __name__ == "__main__":
    config = {"host": "localhost", "port": 27017}
    migrator = MigrateMongoIds(config=config)
    migrator.transform_deployment_id()
    migrator.transform_session_id()
    migrator.transform_parent_id()
